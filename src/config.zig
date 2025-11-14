const std = @import("std");

pub const Action = struct {
    root: ?[]const u8 = null,
    script: []const u8,
    name: []const u8,

    pub fn clone(self: *const Action, allocator: std.mem.Allocator) !Action {
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

    pub fn deinit(self: *const Action, allocator: std.mem.Allocator) void {
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

    pub fn clone(self: *const Configuration, allocator: std.mem.Allocator) !Configuration {
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
            return .{
                .workers = self.workers,
                .preScripts = new_items,
            };
        }

        return .{ .workers = self.workers };
    }

    pub fn deinit(self: *const Configuration, allocator: std.mem.Allocator) void {
        if (self.preScripts) |preScripts| {
            for (preScripts) |p| {
                p.deinit(allocator);
            }
            allocator.free(preScripts);
        }
    }
};
