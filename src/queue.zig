const std = @import("std");
const con = @import("./config.zig");

pub const Queue = struct {
    items: ?[]Cluster = null,

    pub fn clone(self: *const Queue, allocator: std.mem.Allocator) !void {
        _ = self;
        _ = allocator;
    }

    pub fn deinit(self: *const Queue, allocator: std.mem.Allocator) void {
        _ = self;
        _ = allocator;
    }

    pub fn init(allocator: std.mem.Allocator, config: con.Configuration) !Queue {

        // TODO: This name building is copied around should be refactor as it is a common task
        var total: u8 = 0;
        for (config.clusters) |cluster| {
            total += cluster.count;
        }
        var cluster_content = try allocator.alloc(Cluster, total);
        var pos: u8 = 0;
        defer {
            for (cluster_content[0..pos]) |content| content.deinit(allocator);
            allocator.free(cluster_content);
        }

        for (config.clusters) |cluster| {
            if (cluster.count > 1) {
                var mark: u8 = 1;
                while (mark <= cluster.count) {
                    var cluster_actions: []con.Action = undefined;
                    if (cluster.scripts) |scripts| {
                        cluster_actions = try allocator.alloc(con.Action, scripts.len);

                        var actions_pos: u8 = 0;
                        defer {
                            for (cluster_actions[0..actions_pos]) |action| action.deinit(allocator);
                            allocator.free(cluster_actions);
                        }
                        for (scripts) |script| {
                            cluster_actions[actions_pos] = try script.clone(allocator);
                            actions_pos += 1;
                        }
                    }
                    cluster_content[pos] = .{
                        .name = try std.fmt.allocPrint(allocator, "{s}-{d}", .{ cluster.kind, mark }),
                        .context = try std.fmt.allocPrint(allocator, "kind-{s}-{d}", .{ cluster.kind, mark }),
                        .actions = cluster_actions,
                    };
                    mark += 1;
                    pos += 1;
                }
            } else {
                var cluster_actions: []con.Action = undefined;
                if (cluster.scripts) |scripts| {
                    cluster_actions = try allocator.alloc(con.Action, scripts.len);

                    var actions_pos: u8 = 0;
                    defer {
                        for (cluster_actions[0..actions_pos]) |action| action.deinit(allocator);
                        allocator.free(cluster_actions);
                    }
                    for (scripts) |script| {
                        cluster_actions[actions_pos] = try script.clone(allocator);
                        actions_pos += 1;
                    }
                }
                cluster_content[pos] = .{
                    .name = try allocator.dupe(u8, cluster.kind),
                    .context = try std.fmt.allocPrint(allocator, "kind-{s}", .{cluster.kind}),
                    .actions = cluster_actions,
                };
                pos += 1;
            }
        }

        return .{ .items = cluster_content };
    }

    pub fn next(self: *const Queue, allocator: std.mem.Allocator) void {
        _ = self;
        _ = allocator;
    }
};

const Cluster = struct {
    name: []const u8,
    context: []const u8,
    counter: u8 = 0,
    complete: bool = false,
    actions: ?[]con.Action = null,

    pub fn clone(self: *const Cluster, allocator: std.mem.Allocator) !void {
        _ = self;
        _ = allocator;
    }

    pub fn deinit(self: *const Cluster, allocator: std.mem.Allocator) void {
        allocator.free(self.name);
        allocator.free(self.context);

        if (self.actions) |actions| {
            for (actions) |action| action.deinit(allocator);
            allocator.free(actions);
        }
    }

    pub fn init(allocator: std.mem.Allocator, config: con.Configuration) Cluster {
        _ = allocator;
        _ = config;
        return .{};
    }
};
