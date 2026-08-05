#define _DEFAULT_SOURCE
/*
 * security.c -- interactive launcher for the Kali update-automation toolkit.
 *
 * This is the C "base": it draws a menu and dispatches each choice to the
 * Python backend (automation/secauto.py), which does the real work.
 *
 * Build:  make            (produces ./secauto)
 * Run:    ./secauto
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <libgen.h>
#include <sys/wait.h>

#define MAX_PATH_LEN 4096
#define MAX_CMD_LEN  8192

/*
 * Resolve the directory that contains this executable.
 * Uses the Linux-specific /proc/self/exe symlink so the binary can be moved
 * anywhere as long as the automation/ folder stays next to it.
 * Falls back to "." on failure.
 */
static void exe_dir(char *out, size_t outsz)
{
    char buf[MAX_PATH_LEN];
    ssize_t n = readlink("/proc/self/exe", buf, sizeof(buf) - 1);
    /* readlink() does not report truncation: a fully-filled buffer means the
     * real path may be longer than we can hold, so treat that as failure too
     * rather than using a silently truncated (wrong) path. */
    if (n <= 0 || (size_t)n >= sizeof(buf) - 1) {
        snprintf(out, outsz, ".");
        return;
    }
    buf[n] = '\0';
    /* dirname() may modify its argument and/or return a pointer into it,
     * so we use its return value immediately. */
    char *dir = dirname(buf);
    snprintf(out, outsz, "%s", dir);
}

/* Build the absolute path to the Python dispatcher next to this binary. */
static void script_path(char *out, size_t outsz)
{
    char dir[MAX_PATH_LEN];
    exe_dir(dir, sizeof(dir));
    snprintf(out, outsz, "%s/automation/secauto.py", dir);
}

/*
 * Invoke `python3 <script> <action>` and return the child's exit code.
 * `action` is always a hard-coded literal (never user text), so there is no
 * shell-injection surface here; the script path is quoted for safety with
 * spaces in directory names.
 *
 * system() yields a wait-status, not a plain exit code, so we decode it with
 * the WIF* macros: a normal exit returns its code, a signalled child returns
 * 128+signal, matching shell convention.
 */
static int run_action(const char *action)
{
    char script[MAX_PATH_LEN];
    char cmd[MAX_CMD_LEN];

    script_path(script, sizeof(script));

    if (access(script, R_OK) != 0) {
        fprintf(stderr, "Error: cannot find backend script: %s\n", script);
        return -1;
    }

    snprintf(cmd, sizeof(cmd), "python3 \"%s\" %s", script, action);
    printf("\n>> %s\n\n", cmd);

    int status = system(cmd);
    if (status == -1) {
        perror("system");
        return -1;
    }
    if (WIFEXITED(status))
        return WEXITSTATUS(status);
    if (WIFSIGNALED(status))
        return 128 + WTERMSIG(status);
    return -1;
}

static void print_menu(void)
{
    printf("\n");
    printf("================================================\n");
    printf("   Kali Update & Security Automation (secauto)\n");
    printf("================================================\n");
    printf("  1) Update automation    (apt update/upgrade)\n");
    printf("  2) Security scan         (local audit)\n");
    printf("  3) View logs\n");
    printf("  4) Run all               (update + scan)\n");
    printf("  5) Enable 7-hour update automation\n");
    printf("  6) Stop  7-hour update automation\n");
    printf("  7) Schedule status       (next run)\n");
    printf("  0) Exit\n");
    printf("------------------------------------------------\n");
    printf("Choose an option: ");
    fflush(stdout);
}

/*
 * Read a menu choice safely with fgets + strtol (avoids scanf() pitfalls).
 * Returns the parsed number, -1 on EOF, or -2 when the line has no digits.
 */
static int read_choice(void)
{
    char line[64];
    if (!fgets(line, sizeof(line), stdin))
        return -1;                 /* EOF / read error */
    char *end = NULL;
    long val = strtol(line, &end, 10);
    if (end == line)               /* nothing numeric was entered */
        return -2;
    return (int)val;
}

int main(void)
{
    int running = 1;

    while (running) {
        print_menu();
        int choice = read_choice();

        switch (choice) {
        case 1:
            run_action("update");
            break;
        case 2:
            run_action("scan");
            break;
        case 3:
            run_action("logs list");
            break;
        case 4:
            run_action("all");
            break;
        case 5:
            run_action("schedule-enable");
            break;
        case 6:
            run_action("schedule-stop");
            break;
        case 7:
            run_action("schedule-status");
            break;
        case 0:
            printf("Bye.\n");
            running = 0;
            break;
        case -1:                   /* EOF, e.g. piped input ended */
            printf("\n");
            running = 0;
            break;
        default:
            printf("Invalid option. Please choose 0-7.\n");
            break;
        }
    }
    return 0;
}
