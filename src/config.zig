const std = @import("std");

pub const Cluster = struct {
    kind: []const u8,
    count: u8,
    scripts: ?[]Action = null,

    pub fn clone(self: @This(), allocator: std.mem.Allocator) !@This() {
        return .{
            .kind = try allocator.dupe(u8, self.kind),
            .count = self.count,
            .scripts = try self.clone_scripts(allocator),
        };
    }

    pub fn deinit(self: @This(), allocator: std.mem.Allocator) void {
        allocator.free(self.kind);
        if (self.scripts) |scripts| {
            for (scripts) |script| {
                script.deinit(allocator);
            }
            allocator.free(scripts);
        }
    }

    fn clone_scripts(self: @This(), allocator: std.mem.Allocator) !?[]Action {
        if (self.scripts) |scripts| {
            var new_items = try allocator.alloc(Action, scripts.len);

            // On error, deinit any items that were already initialized and free the array.
            var initialized: usize = 0;
            errdefer {
                // deinitialize only the items that were constructed so far
                for (new_items[0..initialized]) |it| it.deinit(allocator);
                allocator.free(new_items);
            }

            // Clone each item; increment `initialized` after a successful clone.
            for (scripts, 0..) |item, i| {
                new_items[i] = try item.clone(allocator);
                initialized += 1;
            }
            return new_items;
        }
        return null;
    }
};

pub const Action = struct {
    root: ?[]const u8 = null,
    script: []const u8,
    name: []const u8,

    pub fn clone(self: @This(), allocator: std.mem.Allocator) !@This() {
        if (self.root) |r| {
            return .{
                .root = try allocator.dupe(u8, r),
                .script = try allocator.dupe(u8, self.script),
                .name = try allocator.dupe(u8, self.name),
            };
        }
        return .{
            .script = try allocator.dupe(u8, self.script),
            .name = try allocator.dupe(u8, self.name),
        };
    }

    pub fn deinit(self: @This(), allocator: std.mem.Allocator) void {
        if (self.root) |root| {
            allocator.free(root);
        }
        allocator.free(self.script);
        allocator.free(self.name);
    }
};

pub const Configuration = struct {
    workers: u8 = 4,
    preScripts: ?[]Action = null,
    clusters: []Cluster,
    postScripts: ?[]Action = null,

    pub fn clone(self: @This(), allocator: std.mem.Allocator) !@This() {
        return .{
            .workers = self.workers,
            .clusters = try self.clone_clusters(allocator),
            .preScripts = try self.clone_preScripts(allocator),
            .postScripts = try self.clone_postScripts(allocator),
        };
    }

    pub fn deinit(self: @This(), allocator: std.mem.Allocator) void {
        if (self.preScripts) |preScripts| {
            for (preScripts) |p| {
                p.deinit(allocator);
            }
            allocator.free(preScripts);
        }
        if (self.postScripts) |postScripts| {
            for (postScripts) |p| {
                p.deinit(allocator);
            }
            allocator.free(postScripts);
        }
        for (self.clusters) |cluster| {
            cluster.deinit(allocator);
        }
        allocator.free(self.clusters);
    }

    fn clone_postScripts(self: @This(), allocator: std.mem.Allocator) !?[]Action {
        if (self.postScripts) |postScripts| {
            var new_items = try allocator.alloc(Action, postScripts.len);

            // On error, deinit any items that were already initialized and free the array.
            var initialized: usize = 0;
            errdefer {
                // deinitialize only the items that were constructed so far
                for (new_items[0..initialized]) |it| it.deinit(allocator);
                allocator.free(new_items);
            }

            // Clone each item; increment `initialized` after a successful clone.
            for (postScripts, 0..) |item, i| {
                new_items[i] = try item.clone(allocator);
                initialized += 1;
            }
            return new_items;
        }
        return null;
    }
    fn clone_preScripts(self: @This(), allocator: std.mem.Allocator) !?[]Action {
        if (self.preScripts) |preScripts| {
            var new_items = try allocator.alloc(Action, preScripts.len);

            // On error, deinit any items that were already initialized and free the array.
            var initialized: usize = 0;
            errdefer {
                // deinitialize only the items that were constructed so far
                for (new_items[0..initialized]) |it| it.deinit(allocator);
                allocator.free(new_items);
            }

            // Clone each item; increment `initialized` after a successful clone.
            for (preScripts, 0..) |item, i| {
                new_items[i] = try item.clone(allocator);
                initialized += 1;
            }
            return new_items;
        }
        return null;
    }

    fn clone_clusters(self: @This(), allocator: std.mem.Allocator) ![]Cluster {
        var new_items = try allocator.alloc(Cluster, self.clusters.len);

        // On error, deinit any items that were already initialized and free the array.
        var initialized: usize = 0;
        errdefer {
            // deinitialize only the items that were constructed so far
            for (new_items[0..initialized]) |it| it.deinit(allocator);
            allocator.free(new_items);
        }

        // Clone each item; increment `initialized` after a successful clone.
        for (self.clusters, 0..) |item, i| {
            new_items[i] = try item.clone(allocator);
            initialized += 1;
        }
        return new_items;
    }
};
