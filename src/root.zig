const std = @import("std");
const config = @import("./config.zig");

pub const Configuration = config.Configuration;

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
