const clap = @import("clap");
const std = @import("std");
const deploy = @import("deploy");

// These are our subcommands.
const SubCommands = enum {
    help,
    create,
    remove,
};

const main_parsers = .{
    .command = clap.parsers.enumeration(SubCommands),
};

const main_params = clap.parseParamsComptime(
    \\-h, --help  Display this help and exit.
    \\<command>
    \\
);

const MainArgs = clap.ResultEx(clap.Help, &main_params, main_parsers);

pub fn main() !void {
    var gpa_state = std.heap.DebugAllocator(.{}){};
    const gpa = gpa_state.allocator();
    defer _ = gpa_state.deinit();

    var stderr_buffer: [4096]u8 = undefined;
    var stderr_writer = std.fs.File.stderr().writer(&stderr_buffer);
    const stderr = &stderr_writer.interface;

    var iter = try std.process.ArgIterator.initWithAllocator(gpa);
    defer iter.deinit();

    _ = iter.next();

    var diag = clap.Diagnostic{};
    var res = clap.parseEx(clap.Help, &main_params, main_parsers, &iter, .{
        .diagnostic = &diag,
        .allocator = gpa,
        .terminating_positional = 0,
    }) catch |err| {
        try diag.reportToFile(.stderr(), err);
        return err;
    };
    defer res.deinit();
    if (res.args.help != 0) {
        try clap.helpToFile(.stderr(), clap.Help, &main_params, .{});
        try stderr.print("    Commands:\n", .{});

        inline for (@typeInfo(SubCommands).@"enum".fields) |field| {
            try stderr.print("      {s}\n", .{field.name});
        }
        try stderr.flush();
        return;
    }

    const command = res.positionals[0] orelse return error.MissingCommand;
    switch (command) {
        .help => {
            try clap.helpToFile(.stderr(), clap.Help, &main_params, .{});
            try stderr.print("    Commands:\n", .{});

            // Print all subcommands from the enum
            inline for (@typeInfo(SubCommands).@"enum".fields) |field| {
                try stderr.print("      {s}\n", .{field.name});
            }
            try stderr.flush();
        },
        .create => try createMain(gpa, &iter, res),
        .remove => try removeMain(gpa, &iter, res),
    }
}

fn createMain(allocator: std.mem.Allocator, iter: *std.process.ArgIterator, main_args: MainArgs) !void {
    _ = main_args;

    const params = comptime clap.parseParamsComptime(
        \\-h, --help  Display this help and exit.
        \\-a, --add   Add the two numbers
        \\-s, --sub   Subtract the two numbers
        \\<CONFIG> Json configuration file.
        \\
    );

    const parsers = comptime .{
        .CONFIG = clap.parsers.string,
    };

    var diag = clap.Diagnostic{};
    var res = clap.parseEx(clap.Help, &params, parsers, iter, .{
        .diagnostic = &diag,
        .allocator = allocator,
    }) catch |err| {
        try diag.reportToFile(.stderr(), err);
        return err; // propagate error
    };
    defer res.deinit();

    if (res.args.help != 0)
        return clap.helpToFile(.stderr(), clap.Help, &params, .{});

    const config_path = res.positionals[0] orelse return error.MissingArg1;
    const config = try deploy.loadConfiguration(allocator, config_path);
    defer config.deinit(allocator);

    if (config.preScripts) |preScripts| {
        for (preScripts) |action| {
            std.debug.print("script: {s}\n", .{action.script});
        }
    }

    var pool: std.Thread.Pool = undefined;
    try pool.init(.{
        .allocator = allocator,
        .n_jobs = config.workers,
    });
    defer pool.deinit();

    var wg: std.Thread.WaitGroup = .{};

    if (config.preScripts) |preScripts| {
        std.debug.print("Starting running preScripts\n", .{});
        for (preScripts) |action| {
            pool.spawnWg(&wg, deploy.runAction, .{ allocator, action });
        }
    }
    wg.wait();
    std.debug.print("Finished running preScripts\n", .{});

    try deploy.createCluster(allocator, config);
    try deploy.applyClusterScripts(allocator, config);

    std.debug.print("all done\n", .{});
}
fn removeMain(gpa: std.mem.Allocator, iter: *std.process.ArgIterator, main_args: MainArgs) !void {
    _ = main_args;

    const params = comptime clap.parseParamsComptime(
        \\-h, --help  Display this help and exit.
        \\-a, --add   Add the two numbers
        \\-s, --sub   Subtract the two numbers
        \\<isize>
        \\<isize>
        \\
    );

    var diag = clap.Diagnostic{};
    var res = clap.parseEx(clap.Help, &params, clap.parsers.default, iter, .{
        .diagnostic = &diag,
        .allocator = gpa,
    }) catch |err| {
        try diag.reportToFile(.stderr(), err);
        return err; // propagate error
    };
    defer res.deinit();

    if (res.args.help != 0)
        return clap.helpToFile(.stderr(), clap.Help, &params, .{});
    const a = res.positionals[0] orelse return error.MissingArg1;
    const b = res.positionals[1] orelse return error.MissingArg1;
    if (res.args.add != 0)
        std.debug.print("added: {}\n", .{a + b});
    if (res.args.sub != 0)
        std.debug.print("subtracted: {}\n", .{a - b});
}
