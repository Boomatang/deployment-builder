const std = @import("std");

pub fn create(allocator: std.mem.Allocator, cluster: []const u8) void {
    std.debug.print("creating cluster: {s}\n", .{cluster});

    const cmd = &[_][]const u8{ "kind", "create", "cluster", "--name", cluster };
    const result = std.process.Child.run(.{
        .allocator = allocator,
        .argv = cmd,
    }) catch |err| {
        std.debug.print("ERROR: failed to run kind create command: {}\n", .{err});
        return;
    };
    defer {
        allocator.free(result.stderr);
        allocator.free(result.stdout);
    }
    std.debug.print("finished creating cluster: {s}\n", .{cluster});
}
