"""THROWAWAY wine2e loop: count first-attempt failures of the Job Object mechanism tests."""
import concurrent.futures as cf
import os
import shutil
import subprocess
import sys

N_NATURAL = int(os.environ.get("N_NATURAL", "48"))
N_INJECT = int(os.environ.get("N_INJECT", "16"))
WORKERS = int(os.environ.get("LOOP_WORKERS", "6"))
env = dict(os.environ, HERMES_TEST_FILE_RETRIES="0")
BASH = shutil.which("bash")  # never System32\\bash.exe (WSL), which CreateProcess finds first
print("bash", BASH, flush=True)
print("sys.executable", sys.executable, "base", getattr(sys, "_base_executable", None), flush=True)


def one(args):
    phase, i, path = args
    r = subprocess.run(
        [BASH, "scripts/run_tests.sh", path, "--", "-k", "TestJobObjectMechanismLive", "-v", "--tb=short"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, stdin=subprocess.DEVNULL,
    )
    out = r.stdout + r.stderr
    nonbreak_failed = "test_non_breakaway_child_killed_by_job_teardown FAILED" in out
    break_failed = "test_breakaway_child_survives_job_teardown FAILED" in out
    passed2 = out.count(" PASSED") >= 2
    return phase, i, r.returncode, nonbreak_failed, break_failed, passed2, out


def run(phase, path, n):
    fails = 0
    shown = 0
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        for ph, i, rc, nb, bk, ok, out in ex.map(one, [(phase, i, path) for i in range(n)]):
            bad = rc != 0
            fails += bad
            print(f"{ph} #{i}: rc={rc} nonbreakaway_failed={nb} breakaway_failed={bk} two_passed={ok}", flush=True)
            if bad and shown < 2:
                shown += 1
                print("---- failure tail ----\n" + out[-6000:] + "\n----", flush=True)
    print(f"RESULT {phase} fails={fails}/{n}", flush=True)
    return fails


run("natural", "tests/hermes_cli/test_gateway_job_teardown_live.py", N_NATURAL)
run("injected", "tests/hermes_cli/test_gateway_job_teardown_inject_live.py", N_INJECT)
