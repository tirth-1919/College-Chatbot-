import asyncio, importlib.util, sys, tempfile, types, uuid
from pathlib import Path
from unittest import TestCase, main
root=Path.cwd(); backend=root/'backend'
app=types.ModuleType('app'); app.__path__=[str(backend/'app')]; sys.modules['app']=app
core=types.ModuleType('app.core'); core.__path__=[]; sys.modules['app.core']=core
cfg=types.ModuleType('app.core.config'); cfg.settings=types.SimpleNamespace(SUPABASE_STORAGE_BUCKET_DOCS='private-pdfs',SUPABASE_URL='https://fake.invalid',SUPABASE_SERVICE_ROLE_KEY='fake'); sys.modules['app.core.config']=cfg
sp=importlib.util.spec_from_file_location('storage_tested',backend/'app/services/storage_service.py'); sm=importlib.util.module_from_spec(sp); sp.loader.exec_module(sm)
configured=True
sm.DocumentStorageService.is_supabase_configured=property(lambda self: configured)
class Bucket:
 def __init__(self, fail=None): self.fail=fail; self.calls=[]
 def upload(self,**kw): self.calls.append(('upload',kw)); self.err('upload'); return {'Key':kw['path']}
 def download(self,path): self.calls.append(('download',path)); self.err('download'); return b'PDF'
 def create_signed_url(self,**kw): self.calls.append(('sign',kw)); self.err('sign'); return {'signedURL':'https://signed.invalid/url'}
 def remove(self,paths): self.calls.append(('remove',paths)); self.err('remove')
 def err(self,op):
  if self.fail==op: raise RuntimeError('mock missing/failure')
class Client:
 def __init__(self,b): self.bucket=b; self.storage=self
 def from_(self,name): self.used_bucket=name; return self.bucket
class Checks(TestCase):
 def make(self,mode=True,bucket=None):
  global configured; configured=mode
  s=sm.DocumentStorageService(); s.local_storage_dir=Path(tempfile.mkdtemp()); b=bucket or Bucket()
  s._supabase_client=Client(b) if mode else None
  return s,b
 def test_upload_success(self):
  s,b=self.make(); c,d=uuid.uuid4(),uuid.uuid4(); p=asyncio.run(s.upload_file(c,d,b'x')); self.assertEqual(p,f'{c}/{d}.pdf'); self.assertEqual(b.calls[0][1]['path'],p); self.assertEqual(s._supabase_client.used_bucket,'private-pdfs')
 def test_upload_failure_no_fallback(self):
  s,b=self.make(bucket=Bucket('upload')); c,d=uuid.uuid4(),uuid.uuid4()
  with self.assertRaises(RuntimeError): asyncio.run(s.upload_file(c,d,b'x'))
  self.assertFalse((s.local_storage_dir/f'{c}/{d}.pdf').exists())
 def test_initialization_failure(self):
  s,_=self.make(); s._supabase_client=None
  with self.assertRaisesRegex(RuntimeError,'could not be initialized'): asyncio.run(s.upload_file(uuid.uuid4(),uuid.uuid4(),b'x'))
 def test_missing_object_no_local_read(self):
  s,b=self.make(bucket=Bucket('download')); p='c/d.pdf'; local=s.local_storage_dir/p; local.parent.mkdir(parents=True); local.write_bytes(b'local')
  with self.assertRaises(FileNotFoundError): asyncio.run(s.get_file_bytes(uuid.uuid4(),p))
 def test_sign_success_exact_path(self):
  s,b=self.make(); p='c/d.pdf'; self.assertEqual(asyncio.run(s.get_signed_url(uuid.uuid4(),p)),'https://signed.invalid/url'); self.assertEqual(b.calls,[('sign',{'path':p,'expires_in':3600})]); self.assertEqual(s._supabase_client.used_bucket,'private-pdfs')
 def test_local_development_flow(self):
  s,_=self.make(False); c,d=uuid.uuid4(),uuid.uuid4(); p=f'{c}/{d}.pdf'; asyncio.run(s.upload_file(c,d,b'local')); self.assertEqual(asyncio.run(s.get_file_bytes(c,p)),b'local'); self.assertEqual(asyncio.run(s.get_signed_url(c,p)),f'/api/v1/college-admin/documents/raw/{p}'); self.assertTrue(asyncio.run(s.delete_file(c,p)))
 def test_configured_delete_failure_preserves_local(self):
  s,b=self.make(bucket=Bucket('remove')); p='c/d.pdf'; f=s.local_storage_dir/p; f.parent.mkdir(parents=True); f.write_bytes(b'keep'); self.assertFalse(asyncio.run(s.delete_file(uuid.uuid4(),p))); self.assertTrue(f.exists())
if __name__=='__main__': main(verbosity=2)
