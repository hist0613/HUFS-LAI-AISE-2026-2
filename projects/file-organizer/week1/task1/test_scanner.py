"""모든 파일은 임시 폴더에 생성한다. 실제 사용자 파일을 사용하지 않는다."""
import io
import json
import os
import stat
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from main import main
from scanner import save_json, scan_files


class ScannerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "한글 폴더"
        self.root.mkdir()

    def make_file(self, name, data=b"sample"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_metadata_order_ids_and_originals(self):
        paths = [self.make_file(name) for name in ["보고서 A.PDF", "하위/노래.mp3", "a"]]
        for path in paths:
            os.utime(path, (0, 0))
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
        files = scan_files(self.root)
        self.assertEqual(files, scan_files(self.root))
        self.assertEqual([f["rel_path"] for f in files], ["a", "보고서 A.PDF", "하위/노래.mp3"])
        self.assertEqual([f["file_id"] for f in files], ["f_0001", "f_0002", "f_0003"])
        self.assertEqual(files[1], dict(file_id="f_0002", rel_path="보고서 A.PDF",
                                      name="보고서 A.PDF", ext=".pdf", size_bytes=6,
                                      mtime="1970-01-01T00:00:00Z", selected=False))
        self.assertEqual(files[0]["ext"], "")
        save_json(files, self.root / "result.json")
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths})

    def test_empty_missing_and_non_directory(self):
        self.assertEqual(scan_files(self.root), [])
        with self.assertRaises(FileNotFoundError):
            scan_files(self.root / "missing")
        with self.assertRaises(NotADirectoryError):
            scan_files(self.make_file("file.txt"))

    def test_exclusions(self):
        for name in [".git/config", ".DS_Store", "desktop.ini", "DESKTOP.INI",
                     ".hidden", ".private/data.txt", "keep.txt", "output.json"]:
            self.make_file(name)
        files = scan_files(self.root, exclude_paths=[self.root / "output.json"])
        self.assertEqual([f["name"] for f in files], ["keep.txt"])

    def test_json_roundtrip_and_no_overwrite(self):
        original = self.make_file("한글.txt")
        files = scan_files(self.root)
        output = save_json(files, self.root / "목록.json")
        text = output.read_text(encoding="utf-8")
        self.assertIn("한글.txt", text)
        self.assertEqual(json.loads(text), files)
        self.assertIs(json.loads(text)[0]["selected"], False)
        self.assertIsInstance(json.loads(text)[0]["size_bytes"], int)
        with self.assertRaises(FileExistsError):
            save_json(files, original)
        self.assertEqual(original.read_bytes(), b"sample")

    def test_cli_success_and_repeat(self):
        self.make_file("과제.pdf")
        output = self.root / "결과.json"
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(main([str(self.root), "-o", str(output)]), 0)
            self.assertEqual(main([str(self.root), "-o", str(output)]), 1)
        self.assertIn("1. 과제.pdf", stdout.getvalue())
        self.assertIn(str(output), stdout.getvalue())
        self.assertIn("이미 존재", stderr.getvalue())
        self.assertEqual(len(json.loads(output.read_text(encoding="utf-8"))), 1)

    def test_cli_missing_paths_and_denied_access(self):
        output = self.root / "result.json"
        with redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(main([str(self.root / "missing"), "-o", str(output)]), 1)
            self.assertEqual(main([str(self.root), "-o", str(self.root / "missing/out.json")]), 1)
            with patch("scanner.os.scandir", side_effect=PermissionError(13, "denied")):
                self.assertEqual(main([str(self.root), "-o", str(output)]), 1)
        self.assertIn("접근 권한", stderr.getvalue())
        self.assertFalse(output.exists())

    def test_symlinks_are_not_followed(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("fake data", encoding="utf-8")
        try:
            (self.root / "outside").symlink_to(outside, target_is_directory=True)
            (self.root / "loop").symlink_to(self.root, target_is_directory=True)
            (self.root / "file-link").symlink_to(outside / "secret.txt")
        except OSError as error:
            if getattr(error, "winerror", None) != 1314:
                raise
            self.skipTest("심볼릭 링크 생성 권한 없음 (WinError 1314)")
        self.assertEqual(scan_files(self.root), [])

    def test_cli_output_permission_error(self):
        with patch("scanner.Path.open", side_effect=PermissionError(13, "denied")):
            with redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(main([str(self.root), "-o", str(self.root / "out.json")]), 1)
        self.assertIn("접근 권한", stderr.getvalue())
        self.assertFalse((self.root / "out.json").exists())

    @unittest.skipUnless(os.name == "nt", "Windows 정션 테스트")
    def test_windows_junctions_are_not_followed(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_bytes(b"fake data")
        for name, target in [("outside", outside), ("loop", self.root)]:
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(self.root / name), str(target)],
                capture_output=True,
            )
            if result.returncode and b"Access is denied" in result.stderr:
                self.skipTest("현재 환경에서 정션 생성 접근 거부")
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(scan_files(self.root), [])

    def test_link_attributes_are_excluded(self):
        for mode, attributes in [(stat.S_IFLNK, 0),
                                 (stat.S_IFDIR, stat.FILE_ATTRIBUTE_REPARSE_POINT)]:
            metadata = SimpleNamespace(st_mode=mode, st_file_attributes=attributes)
            entry = SimpleNamespace(name="link", stat=lambda **kwargs: metadata)
            with patch("scanner.os.scandir") as scandir:
                scandir.return_value.__enter__.return_value = [entry]
                self.assertEqual(scan_files(self.root), [])
                scandir.assert_called_once_with(self.root)

    @unittest.skipUnless(os.name == "nt", "Windows 숨김 속성 테스트")
    def test_windows_hidden_attributes(self):
        import ctypes
        paths = [self.make_file("hidden.txt"), self.root / "hidden-dir"]
        paths[1].mkdir()
        (paths[1] / "inside.txt").write_bytes(b"sample")
        for path in paths:
            self.assertTrue(ctypes.windll.kernel32.SetFileAttributesW(str(path), 2))
            self.addCleanup(ctypes.windll.kernel32.SetFileAttributesW, str(path), 128)
        self.assertEqual(scan_files(self.root), [])


if __name__ == "__main__":
    unittest.main()
