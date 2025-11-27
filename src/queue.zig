const std = @import("std");
const con = @import("./config.zig");

pub const Queue = struct {
    items: ?[]Cluster = null,
    mutex: std.Thread.Mutex,

    pub fn clone(self: @This(), allocator: std.mem.Allocator) !void {
        _ = self;
        _ = allocator;
    }

    pub fn deinit(self: @This(), allocator: std.mem.Allocator) void {
        if (self.items) |items| {
            for (items) |item| item.deinit(allocator);
            allocator.free(items);
        }
    }

    pub fn init(allocator: std.mem.Allocator, config: con.Configuration) !@This() {

        // TODO: This name building is copied around should be refactor as it is a common task
        var total: u8 = 0;
        for (config.clusters) |cluster| {
            total += cluster.count;
        }
        var cluster_content = try allocator.alloc(Cluster, total);
        var pos: u8 = 0;
        errdefer {
            for (cluster_content[0..pos]) |content| content.deinit(allocator);
            allocator.free(cluster_content);
        }

        for (config.clusters) |cluster| {
            if (cluster.count > 1) {
                var mark: u8 = 1;
                while (mark <= cluster.count) {
                    var cluster_actions: ?[]con.Action = null;
                    if (cluster.scripts) |scripts| {
                        cluster_actions = try allocator.alloc(con.Action, scripts.len);

                        var actions_pos: u8 = 0;
                        errdefer {
                            if (cluster_actions) |actions| {
                                for (actions[0..actions_pos]) |action| action.deinit(allocator);
                                allocator.free(actions);
                            }
                        }
                        for (scripts) |script| {
                            cluster_actions.?[actions_pos] = try script.clone(allocator);
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
                var cluster_actions: ?[]con.Action = null;
                if (cluster.scripts) |scripts| {
                    cluster_actions = try allocator.alloc(con.Action, scripts.len);

                    var actions_pos: u8 = 0;
                    errdefer {
                        if (cluster_actions) |actions| {
                            for (actions[0..actions_pos]) |action| action.deinit(allocator);
                            allocator.free(actions);
                        }
                    }
                    for (scripts) |script| {
                        cluster_actions.?[actions_pos] = try script.clone(allocator);
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

        return .{ .items = cluster_content, .mutex = std.Thread.Mutex{} };
    }

    pub fn next(self: *@This(), allocator: std.mem.Allocator) ?Action {
        _ = allocator;
        self.mutex.lock();
        defer self.mutex.unlock();

        var pos = struct { lowest: u8 = 255, idx: usize = 0, active: bool = false }{};

        if (self.items) |items| {
            for (items, 0..) |item, i| {
                if (item.active() and item.counter < pos.lowest) {
                    pos.lowest = item.counter;
                    pos.idx = i;
                    pos.active = true;
                }
            }
        }

        if (pos.active) {
            return .{
                .name = self.items.?[pos.idx].name,
                .context = self.items.?[pos.idx].context,
                .action = self.items.?[pos.idx].next(),
            };
        }

        return null;
    }
};

const Action = struct {
    name: []const u8,
    context: []const u8,
    action: ?con.Action = null,
};

const Cluster = struct {
    name: []const u8,
    context: []const u8,
    counter: u8 = 0,
    complete: bool = false,
    actions: ?[]con.Action = null,

    pub fn clone(self: @This(), allocator: std.mem.Allocator) !void {
        _ = self;
        _ = allocator;
    }

    pub fn deinit(self: @This(), allocator: std.mem.Allocator) void {
        allocator.free(self.name);
        allocator.free(self.context);

        if (self.actions) |actions| {
            for (actions) |action| action.deinit(allocator);
            allocator.free(actions);
        }
    }

    pub fn init(allocator: std.mem.Allocator, config: con.Configuration) @This() {
        _ = allocator;
        _ = config;
        return .{};
    }

    pub fn active(self: @This()) bool {
        return !self.complete;
    }

    pub fn next(self: *Cluster) ?con.Action {
        if (self.complete) return null;

        if (self.actions) |actions| {
            const action = actions[self.counter];
            self.counter += 1;
            if (self.counter >= actions.len) {
                self.complete = true;
            }
            return action;
        }

        return null;
    }
};
