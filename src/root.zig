const std = @import("std");
const con = @import("./config.zig");
const kind = @import("./kind.zig");
const queue = @import("./queue.zig");

pub fn loadConfiguration(allocator: std.mem.Allocator, path: []const u8) !con.Configuration {
    std.debug.print("path: {s}\n", .{path});

    const file = try std.fs.cwd().openFile(path, .{ .mode = .read_only });
    defer file.close();

    const file_size = try file.getEndPos();
    const buffer = try allocator.alloc(u8, file_size);
    defer allocator.free(buffer);

    _ = try file.readAll(buffer);

    const parsed = try std.json.parseFromSlice(con.Configuration, allocator, buffer, .{});

    defer parsed.deinit();
    return parsed.value.clone(allocator);
}

pub const actionOpts = struct {
    name: ?[]const u8 = null,
    context: ?[]const u8 = null,
};

pub fn poolActions(allocator: std.mem.Allocator, running: []const u8, actions: []con.Action, workers: usize, opts: actionOpts) !void {
    var pool: std.Thread.Pool = undefined;
    try pool.init(.{
        .allocator = allocator,
        .n_jobs = workers,
    });
    defer pool.deinit();

    var wg: std.Thread.WaitGroup = .{};

    std.debug.print("Starting running {s}\n", .{running});
    std.mem.reverse(con.Action, actions);
    for (actions) |action| {
        pool.spawnWg(&wg, runAction, .{ allocator, action, opts });
    }
    wg.wait();
    std.debug.print("Finished running {s}\n", .{running});
}

pub fn runAction(allocator: std.mem.Allocator, action: con.Action, opts: actionOpts) void {
    std.debug.print("Starting action: {s}, opts: name: {s}, context: {s}\n", .{ action.name, if (opts.name) |name| name else "", if (opts.context) |context| context else "" });
    const result = std.process.Child.run(.{ .allocator = allocator, .cwd = action.root, .argv = &[_][]const u8{action.script} }) catch |err| {
        std.debug.print("An error trying to run script: {s}\nerror: {}\n", .{ action.script, err });
        return;
    };

    defer {
        allocator.free(result.stdout);
        allocator.free(result.stderr);
    }

    std.debug.print("Finished running action: {s}, opts: name: {s}, context: {s}\n", .{ action.name, if (opts.name) |name| name else "", if (opts.context) |context| context else "" });
}

pub fn createCluster(allocator: std.mem.Allocator, config: con.Configuration) !void {
    // TODO: This name building is copied around should be refactor as it is a common task
    var total: u8 = 0;
    for (config.clusters) |cluster| {
        total += cluster.count;
    }

    var cluster_names = try allocator.alloc([]const u8, total);
    var pos: u8 = 0;
    defer {
        for (cluster_names[0..pos]) |name| allocator.free(name);
        allocator.free(cluster_names);
    }

    for (config.clusters) |cluster| {
        if (cluster.count > 1) {
            var mark: u8 = 1;
            while (mark <= cluster.count) {
                cluster_names[pos] = try std.fmt.allocPrint(allocator, "{s}-{d}", .{ cluster.kind, mark });
                mark += 1;
                pos += 1;
            }
        } else {
            cluster_names[pos] = try allocator.dupe(u8, cluster.kind);
            pos += 1;
        }
    }

    var wg: std.Thread.WaitGroup = .{};
    std.debug.print("Starting to create cluster\n", .{});
    var pool: std.Thread.Pool = undefined;
    try pool.init(.{
        .allocator = allocator,
        .n_jobs = config.workers,
    });
    defer pool.deinit();
    for (cluster_names) |name| {
        pool.spawnWg(&wg, kind.create, .{ allocator, name });
    }
    wg.wait();
    std.debug.print("Finished creating clusters\n", .{});
}

fn workerThread(allocator: std.mem.Allocator, q: *queue.Queue, thread_id: usize) void {
    std.debug.print("Thread {d} started\n", .{thread_id});

    while (q.next(allocator)) |task| {
        std.debug.print("Thread {d}: Processing task {s}\n", .{
            thread_id,
            task.name,
        });
        if (task.action) |action| {
            runAction(allocator, action, actionOpts{ .name = task.name, .context = task.context });
        } else {
            std.debug.print("ERROR: Tried running a task with no action: {s}", .{task.name});
        }
    }

    std.debug.print("Thread {d} finished\n", .{thread_id});
}

pub fn applyClusterScripts(allocator: std.mem.Allocator, config: con.Configuration) !void {
    std.debug.print("Start running cluster scripts\n", .{});

    var q = try queue.Queue.init(allocator, config);
    defer q.deinit(allocator);

    std.debug.print("Start loop to get items from the queue.\n", .{});
    const threads = try allocator.alloc(std.Thread, config.workers);
    defer allocator.free(threads);

    for (0..config.workers) |i| {
        threads[i] = try std.Thread.spawn(.{}, workerThread, .{ allocator, &q, i });
    }

    std.debug.print("Wait for all theads to complete\n", .{});
    for (0..config.workers) |i| {
        threads[i].join();
    }

    std.debug.print("Finished running cluster scripts\n", .{});
}
