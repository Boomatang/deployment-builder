const std = @import("std");

pub fn create(allocator: std.mem.Allocator, cluster: []const u8) void {
    _ = allocator;
    std.debug.print("creating cluster: {s}\n", .{cluster});
}
