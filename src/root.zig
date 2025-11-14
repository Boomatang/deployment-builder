const std = @import("std");
const config = @import("./config.zig");
const kind = @import("./kind.zig");

pub fn loadConfiguration(allocator: std.mem.Allocator, path: []const u8) !config.Configuration {
    std.debug.print("path: {s}\n", .{path});

    const file = try std.fs.cwd().openFile(path, .{ .mode = .read_only });
    defer file.close();

    const file_size = try file.getEndPos();
    const buffer = try allocator.alloc(u8, file_size);
    defer allocator.free(buffer);

    _ = try file.readAll(buffer);

    const parsed = try std.json.parseFromSlice(config.Configuration, allocator, buffer, .{});

    defer parsed.deinit();
    return parsed.value.clone(allocator);
}

pub fn runAction(allocator: std.mem.Allocator, action: config.Action) void {
    std.debug.print("starting action: {s}\n", .{action.name});
    const result = std.process.Child.run(.{ .allocator = allocator, .cwd = action.root, .argv = &[_][]const u8{action.script} }) catch |err| {
        std.debug.print("An error trying to run script: {s}\nerror: {}\n", .{ action.script, err });
        return;
    };

    defer {
        allocator.free(result.stdout);
        allocator.free(result.stderr);
    }

    std.debug.print("finished running action: {s}\n", .{action.name});
}

pub fn createCluster(allocator: std.mem.Allocator, c: config.Configuration) !void {
    var total: u8 = 0;
    for (c.clusters) |cluster| {
        total += cluster.count;
    }
    var cluster_names = try allocator.alloc([]const u8, total);
    var pos: u8 = 0;
    defer {
        for (cluster_names[0..pos]) |name| allocator.free(name);
        allocator.free(cluster_names);
    }

    for (c.clusters) |cluster| {
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
        .n_jobs = c.workers,
    });
    defer pool.deinit();
    for (cluster_names) |name| {
        pool.spawnWg(&wg, kind.create, .{ allocator, name });
    }
    wg.wait();
    std.debug.print("Finished creating clusters\n", .{});
}
