"""Manifest integrity with bounded read concurrency and complete cold objects."""
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from mantleos import cartridge


class CartridgeManifestTests(unittest.TestCase):
    def test_streams_last_byte_and_checks_size_without_timestamp_trust(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            file=root/'cold.bin'
            file.write_bytes(b'first'+b'x'*(1024*1024+31)+b'last')
            manifest=cartridge.write_manifest(root)
            self.assertEqual(cartridge.verify_manifest(root),manifest)
            metadata=file.stat()
            with file.open('r+b') as stream:
                stream.seek(-1,2);stream.write(b'!')
            os.utime(file,ns=(metadata.st_atime_ns,metadata.st_mtime_ns))
            with self.assertRaisesRegex(ValueError,'Manifest mismatch: cold.bin'):
                cartridge.verify_manifest(root)
            # A matching digest cannot substitute for the declared byte length.
            manifest=cartridge.write_manifest(root)
            manifest['files'][0]['bytes']-=1
            import json
            (root/'MANIFEST.json').write_text(json.dumps(manifest),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'Manifest mismatch: cold.bin'):
                cartridge.verify_manifest(root)

    def test_parallel_file_handles_are_bounded_and_all_files_are_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for index in range(80):
                (root/f'piece-{index:03}.bin').write_bytes(bytes([index])*8192)
            manifest=cartridge.write_manifest(root)
            original=Path.open
            lock=threading.Lock();gate=threading.Event()
            counters={'active':0,'peak':0,'opened':0}

            class Observed:
                def __init__(self,stream):self.stream=stream
                def __enter__(self):
                    with lock:
                        counters['active']+=1;counters['opened']+=1
                        counters['peak']=max(counters['peak'],counters['active'])
                        if counters['active']>=2:gate.set()
                    # A sequential regression fails once, rather than hanging
                    # for every file. Cleanup always waits for the reader pool.
                    if not gate.wait(3):gate.set()
                    return self.stream
                def __exit__(self,*args):
                    try:self.stream.close()
                    finally:
                        with lock:counters['active']-=1

            def opened(path,mode='r',*args,**kwargs):
                stream=original(path,mode,*args,**kwargs)
                return Observed(stream) if mode=='rb' and path.name.startswith('piece-') else stream

            with patch.object(Path,'open',opened):
                self.assertEqual(cartridge.verify_manifest(root),manifest)
                self.assertEqual(counters['opened'],80)
                (root/'piece-000.bin').write_bytes(b'changed!')
                with self.assertRaisesRegex(ValueError,'Manifest mismatch: piece-000.bin'):
                    cartridge.verify_manifest(root)
                self.assertEqual(counters['active'],0,'Failed verification returned with open readers')
            self.assertEqual(counters['active'],0)
            self.assertGreaterEqual(counters['peak'],2)
            self.assertLessEqual(counters['peak'],4)

    def test_parallel_path_still_rejects_extra_missing_and_corrupted_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for index in range(80):(root/f'piece-{index:03}.bin').write_bytes(b'original')
            cartridge.write_manifest(root)
            (root/'piece-063.bin').write_bytes(b'changed!')
            with self.assertRaisesRegex(ValueError,'Manifest mismatch: piece-063.bin'):
                cartridge.verify_manifest(root)
            (root/'piece-063.bin').write_bytes(b'original')
            missing=root/'piece-079.bin';missing.unlink()
            with self.assertRaisesRegex(ValueError,'inventory mismatch'):
                cartridge.verify_manifest(root)
            missing.write_bytes(b'original');(root/'extra.bin').write_bytes(b'extra')
            with self.assertRaisesRegex(ValueError,'inventory mismatch'):
                cartridge.verify_manifest(root)


if __name__=='__main__':unittest.main()
