import os
import subprocess
import tarfile
import tempfile
import tomllib
import unittest
from pathlib import Path


class EntrypointTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=Path.home())
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.home = self.root / "home"
        self.t3_home = self.home / ".t3"
        self.launcher = self.home / ".local/bin/t3"
        self.version_file = self.t3_home / ".workspace-version"
        self.network_log = self.root / "network.log"
        self.fake_bin = self.root / "bin"
        self.fake_bin.mkdir()
        self.env = dict(
            os.environ,
            HOME=str(self.home),
            T3CODE_HOME=str(self.t3_home),
            CODEX_HOME=str(self.home / ".codex"),
            T3CODE_CHANNEL="stable",
            T3CODE_UPDATE_ON_START="true",
            TEST_NETWORK_LOG=str(self.network_log),
            TEST_INSTALLER=str(self.root / "installer.sh"),
            TEST_CANDIDATE=str(self.root / "candidate"),
            PATH=f"{self.fake_bin}:{os.environ['PATH']}",
        )
        self.write_executable(
            self.fake_bin / "curl",
            """#!/bin/sh
echo requested >> "$TEST_NETWORK_LOG"
[ "${TEST_DOWNLOAD_FAIL:-false}" = false ] || exit 22
while [ "$#" -gt 0 ]; do
  if [ "$1" = -o ]; then cp "$TEST_INSTALLER" "$2"; exit 0; fi
  shift
done
exit 1
""",
        )
        self.write_executable(
            self.root / "installer.sh",
            """#!/bin/sh
set -eu
[ "${TEST_INSTALL_FAIL:-false}" = false ] || exit 1
mkdir -p "$T3CODE_INSTALL_BIN_DIR"
cp "$TEST_CANDIDATE" "$T3CODE_INSTALL_BIN_DIR/t3"
chmod +x "$T3CODE_INSTALL_BIN_DIR/t3"
printf '%s' "$T3CODE_CHANNEL" > "$T3CODE_HOME/installed-channel"
""",
        )
        self.runtime(self.root / "candidate", "t3 v2")

    def write_executable(self, path, contents):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
        path.chmod(0o755)

    def runtime(self, path, version):
        self.write_executable(
            path,
            f"""#!/bin/sh
if [ "$1" = --version ]; then
  echo '{version}'
else
  mkdir -p "$T3CODE_HOME/userdata"
  printf '%s' launched > "$T3CODE_HOME/userdata/state"
fi
""",
        )

    def cached_runtime(self, version="t3 v1"):
        self.runtime(self.launcher, version)
        self.version_file.parent.mkdir(parents=True, exist_ok=True)
        self.version_file.write_text(version + "\n")

    def run_entrypoint(self, **overrides):
        return subprocess.run(
            ["/usr/local/bin/workspace-entrypoint", "t3", "serve"],
            check=False,
            env=dict(self.env, **overrides),
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_first_start_installs_even_when_update_checks_are_disabled(self):
        result = self.run_entrypoint(T3CODE_UPDATE_ON_START="false")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.version_file.read_text(), "t3 v2\n")
        config = tomllib.loads((self.home / ".codex/config.toml").read_text())
        self.assertEqual(config["sandbox_mode"], "danger-full-access")
        self.assertEqual(config["approval_policy"], "on-request")

    def test_disabled_checks_use_cached_runtime_and_preserve_user_config(self):
        self.cached_runtime()
        config = self.home / ".codex/config.toml"
        config.parent.mkdir(parents=True)
        config.write_text("# user configuration\n")
        result = self.run_entrypoint(T3CODE_UPDATE_ON_START="false")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.network_log.exists())
        self.assertEqual(config.read_text(), "# user configuration\n")
        self.assertEqual(self.version_file.read_text(), "t3 v1\n")

    def test_failed_download_falls_back_to_cached_runtime(self):
        self.cached_runtime()
        result = self.run_entrypoint(TEST_DOWNLOAD_FAIL="true")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("using the cached installation", result.stderr)
        self.assertEqual(self.version_file.read_text(), "t3 v1\n")

    def test_failed_install_falls_back_to_cached_runtime(self):
        self.cached_runtime()
        result = self.run_entrypoint(TEST_INSTALL_FAIL="true")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.version_file.read_text(), "t3 v1\n")

    def test_failed_first_install_reports_missing_runtime(self):
        result = self.run_entrypoint(TEST_DOWNLOAD_FAIL="true")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no cached runtime exists", result.stderr)
        self.assertFalse(self.version_file.exists())

    def test_existing_state_is_snapshotted_on_first_adoption(self):
        state = self.t3_home / "userdata/state"
        state.parent.mkdir(parents=True)
        state.write_text("existing workspace")
        result = self.run_entrypoint()
        self.assertEqual(result.returncode, 0, result.stderr)
        with tarfile.open(self.t3_home / "backups/before-upgrade.tar.gz") as archive:
            self.assertEqual(archive.extractfile("userdata/state").read(), b"existing workspace")

    def test_broken_cached_runtime_fails_visibly(self):
        self.cached_runtime()
        self.write_executable(self.launcher, "#!/bin/sh\nexit 1\n")
        result = self.run_entrypoint(T3CODE_UPDATE_ON_START="false")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cached T3 runtime does not run", result.stderr)

    def test_upgrade_snapshots_state_before_server_changes_it(self):
        self.cached_runtime()
        state = self.t3_home / "userdata/state"
        state.parent.mkdir()
        state.write_text("before upgrade")
        result = self.run_entrypoint(T3CODE_CHANNEL="nightly")
        self.assertEqual(result.returncode, 0, result.stderr)
        backup = self.t3_home / "backups/before-upgrade.tar.gz"
        with tarfile.open(backup) as archive:
            self.assertEqual(archive.extractfile("userdata/state").read(), b"before upgrade")
        self.assertEqual(Path(str(backup) + ".version").read_text(), "t3 v1\n")
        self.assertEqual(state.read_text(), "launched")
        self.assertEqual((self.t3_home / "installed-channel").read_text(), "nightly")

    def test_same_version_preserves_existing_backup(self):
        self.cached_runtime("t3 v2")
        (self.t3_home / "userdata").mkdir()
        backup = self.t3_home / "backups/before-upgrade.tar.gz"
        backup.parent.mkdir()
        backup.write_bytes(b"previous backup")
        result = self.run_entrypoint()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(backup.read_bytes(), b"previous backup")

    def test_external_update_is_snapshotted_when_checks_are_disabled(self):
        self.cached_runtime()
        self.runtime(self.launcher, "t3 v2")
        (self.t3_home / "userdata").mkdir()
        result = self.run_entrypoint(T3CODE_UPDATE_ON_START="false")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.t3_home / "backups/before-upgrade.tar.gz").exists())
        self.assertFalse(self.network_log.exists())

    def test_snapshot_failure_stops_before_launch_and_keeps_previous_backup(self):
        self.cached_runtime()
        (self.t3_home / "userdata").mkdir()
        backup = self.t3_home / "backups/before-upgrade.tar.gz"
        backup.parent.mkdir()
        backup.write_bytes(b"previous backup")
        self.write_executable(self.fake_bin / "tar", "#!/bin/sh\nexit 1\n")
        result = self.run_entrypoint()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot snapshot T3 state", result.stderr)
        self.assertEqual(backup.read_bytes(), b"previous backup")
        self.assertEqual(self.version_file.read_text(), "t3 v1\n")

    def test_invalid_settings_fail_before_network_access(self):
        for overrides in ({"T3CODE_CHANNEL": "invalid"}, {"T3CODE_UPDATE_ON_START": "invalid"}):
            with self.subTest(overrides=overrides):
                result = self.run_entrypoint(**overrides)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.network_log.exists())


if __name__ == "__main__":
    unittest.main()
