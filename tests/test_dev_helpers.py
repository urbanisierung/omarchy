"""Tests for the gml, gdone, gup, gsync and pp helpers in bin/.

Each test builds throwaway git repos in a temp dir (a bare "origin", optionally
a bare "upstream", and a working clone). pnpm and fzf are replaced by fakes
that log their arguments, so nothing touches the network or real projects.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"

FAKE_PM = """#!/bin/bash
echo "$(basename "$0") $*" >> "$TEST_LOG"
"""

# Fake fzf: pick the first line whose name starts with $FZF_PICK.
FAKE_FZF = """#!/bin/bash
grep -m1 "^${FZF_PICK}" || exit 1
"""


@unittest.skipUnless(shutil.which("git") and shutil.which("jq"), "needs git and jq")
class DevHelpersTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.log = self.tmp / "log"
        self.log.touch()
        fakes = self.tmp / "fakes"
        fakes.mkdir()
        for name, body in (("pnpm", FAKE_PM), ("npm", FAKE_PM), ("fzf", FAKE_FZF)):
            p = fakes / name
            p.write_text(body)
            p.chmod(0o755)
        home = self.tmp / "home"
        home.mkdir()
        self.env = {
            "PATH": f"{BIN}:{fakes}:{os.environ['PATH']}",
            "HOME": str(home),
            "TEST_LOG": str(self.log),
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
            "GIT_CONFIG_GLOBAL": str(home / ".gitconfig"),
            "GIT_CONFIG_NOSYSTEM": "1",
        }
        self.git("config", "--global", "init.defaultBranch", "main", cwd=self.tmp)
        self.git("config", "--global", "pull.rebase", "false", cwd=self.tmp)

        self.origin = self.tmp / "origin.git"
        self.git("init", "--bare", "-q", str(self.origin), cwd=self.tmp)
        seed = self.tmp / "seed"
        self.git("clone", "-q", str(self.origin), str(seed), cwd=self.tmp)
        self.commit(seed, "README", "hi")
        self.git("push", "-q", "origin", "main", cwd=seed)
        self.work = self.tmp / "work"
        self.git("clone", "-q", str(self.origin), str(self.work), cwd=self.tmp)

    # helpers ---------------------------------------------------------------

    def run_cmd(self, *args, cwd=None, extra_env=None, check=True):
        env = {**self.env, **(extra_env or {})}
        r = subprocess.run(list(args), cwd=cwd or self.work, env=env,
                           capture_output=True, text=True)
        if check and r.returncode != 0:
            self.fail(f"{args} failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
        return r

    def git(self, *args, cwd=None):
        return self.run_cmd("git", *args, cwd=cwd).stdout.strip()

    def commit(self, repo, name, content, msg=None):
        (Path(repo) / name).write_text(content)
        self.git("add", name, cwd=repo)
        self.git("commit", "-qm", msg or f"change {name}", cwd=repo)

    def push_from_other_clone(self, name, content):
        other = self.tmp / f"other-{name.replace('/', '_')}"
        if not other.exists():
            self.git("clone", "-q", str(self.origin), str(other), cwd=self.tmp)
        else:
            self.git("pull", "-q", cwd=other)
        self.commit(other, name, content)
        self.git("push", "-q", "origin", "main", cwd=other)

    def logged(self):
        return self.log.read_text().splitlines()

    # omarchy-git-main-branch ----------------------------------------------

    def test_main_branch_detects_master(self):
        self.git("branch", "-m", "main", "master")
        self.git("remote", "set-head", "origin", "-d")
        self.git("update-ref", "-d", "refs/remotes/origin/main")
        out = self.run_cmd("omarchy-git-main-branch").stdout.strip()
        self.assertEqual(out, "master")

    # gml -------------------------------------------------------------------

    def test_gml_switches_to_main_and_pulls(self):
        self.git("switch", "-qc", "feature")
        self.push_from_other_clone("new.txt", "x")
        self.run_cmd("gml")
        self.assertEqual(self.git("branch", "--show-current"), "main")
        self.assertTrue((self.work / "new.txt").exists())

    # gdone -----------------------------------------------------------------

    def test_gdone_pushes_switches_pulls_and_cleans(self):
        # An old branch that is merged into main -> should be deleted.
        self.git("branch", "old-merged")
        self.git("switch", "-qc", "feature")
        self.commit(self.work, "f.txt", "feature work")
        self.push_from_other_clone("upstream-change.txt", "y")

        self.run_cmd("gdone")

        self.assertEqual(self.git("branch", "--show-current"), "main")
        self.assertTrue((self.work / "upstream-change.txt").exists())
        remote_branches = self.git("ls-remote", "--heads", "origin")
        self.assertIn("refs/heads/feature", remote_branches)
        local = self.git("branch", "--format=%(refname:short)").split()
        self.assertIn("feature", local)
        self.assertNotIn("old-merged", local)

    def test_gdone_keeps_just_pushed_branch_even_without_commits(self):
        self.git("switch", "-qc", "empty-feature")
        self.run_cmd("gdone")
        self.assertIn("empty-feature", self.git("branch", "--format=%(refname:short)").split())

    def test_gdone_refuses_with_uncommitted_changes(self):
        self.git("switch", "-qc", "feature")
        (self.work / "README").write_text("dirty")
        r = self.run_cmd("gdone", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("uncommitted", r.stderr)
        self.assertEqual(self.git("branch", "--show-current"), "feature")
        self.assertNotIn("feature", self.git("ls-remote", "--heads", "origin"))

    def test_gdone_lists_gone_branches_without_deleting(self):
        self.git("switch", "-qc", "squashed")
        self.commit(self.work, "s.txt", "s")
        self.git("push", "-qu", "origin", "squashed")
        self.git("push", "-q", "origin", "--delete", "squashed")
        self.git("switch", "-qc", "next")
        r = self.run_cmd("gdone")
        self.assertIn("squashed", r.stdout)
        self.assertIn("squashed", self.git("branch", "--format=%(refname:short)").split())

    # gup -------------------------------------------------------------------

    def setup_pnpm_repo(self):
        self.push_from_other_clone("pnpm-lock.yaml", "v1")
        self.git("pull", "-q")
        (self.work / "node_modules").mkdir()

    def test_gup_installs_when_lockfile_changes(self):
        self.setup_pnpm_repo()
        self.push_from_other_clone("pnpm-lock.yaml", "v2")
        self.run_cmd("gup")
        self.assertEqual(self.logged(), ["pnpm install"])

    def test_gup_skips_install_when_lockfile_unchanged(self):
        self.setup_pnpm_repo()
        self.push_from_other_clone("src.ts", "code")
        r = self.run_cmd("gup")
        self.assertEqual(self.logged(), [])
        self.assertIn("unchanged", r.stdout)

    def test_gup_installs_when_node_modules_missing(self):
        self.setup_pnpm_repo()
        (self.work / "node_modules").rmdir()
        self.run_cmd("gup")
        self.assertEqual(self.logged(), ["pnpm install"])

    # gsync -----------------------------------------------------------------

    def test_gsync_merges_origin_main(self):
        self.git("switch", "-qc", "feature")
        self.commit(self.work, "f.txt", "f")
        self.push_from_other_clone("main-change.txt", "m")
        self.run_cmd("gsync")
        self.assertEqual(self.git("branch", "--show-current"), "feature")
        self.assertTrue((self.work / "main-change.txt").exists())
        self.assertTrue((self.work / "f.txt").exists())

    def test_gsync_prefers_upstream_remote(self):
        upstream = self.tmp / "upstream.git"
        self.git("clone", "-q", "--bare", str(self.origin), str(upstream), cwd=self.tmp)
        up_work = self.tmp / "up-work"
        self.git("clone", "-q", str(upstream), str(up_work), cwd=self.tmp)
        self.commit(up_work, "from-upstream.txt", "u")
        self.git("push", "-q", "origin", "main", cwd=up_work)
        self.git("remote", "add", "upstream", str(upstream))

        r = self.run_cmd("gsync")
        self.assertIn("upstream/main", r.stdout)
        self.assertTrue((self.work / "from-upstream.txt").exists())

    # pp --------------------------------------------------------------------

    def write_package(self, scripts, lock="pnpm-lock.yaml", **extra):
        (self.work / "package.json").write_text(json.dumps({"scripts": scripts, **extra}))
        if lock:
            (self.work / lock).write_text("")

    def test_pp_runs_exact_script_with_args(self):
        self.write_package({"build": "tsc", "test": "vitest"})
        self.run_cmd("pp", "test", "--watch")
        self.assertEqual(self.logged(), ["pnpm run test --watch"])

    def test_pp_picks_with_fzf_from_subdirectory(self):
        self.write_package({"build": "tsc", "dev": "vite"})
        sub = self.work / "src" / "deep"
        sub.mkdir(parents=True)
        self.run_cmd("pp", cwd=sub, extra_env={"FZF_PICK": "dev"})
        self.assertEqual(self.logged(), ["pnpm run dev"])

    def test_pp_uses_package_manager_field(self):
        self.write_package({"build": "tsc"}, lock=None, packageManager="npm@10.0.0")
        self.run_cmd("pp", "build")
        self.assertEqual(self.logged(), ["npm run build"])

    def test_pp_without_package_json_fails(self):
        r = self.run_cmd("pp", check=False, cwd=self.tmp)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no package.json", r.stderr)


if __name__ == "__main__":
    unittest.main()
