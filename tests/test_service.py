import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest

spec=importlib.util.spec_from_file_location('service',Path(__file__).parents[1]/'src/service.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class FakeHttp:
    def __init__(self):self.calls=[];self.responses=[]
    def request(self,url,**kwargs):
        self.calls.append((url,kwargs))
        result=self.responses.pop(0)
        if isinstance(result,Exception):raise result
        return result
class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.http=FakeHttp();self.client=s.Client(self.tmp.name,self.http)
    def tearDown(self):self.tmp.cleanup()
    def login(self):
        self.http.responses=[(200,{'code_challenge_methods_supported':['S256']})]
        if not (self.client.directory/'registrations.json').exists():self.http.responses.append((200,{'client_id':'client','client_secret':'SECRET'}))
        self.http.responses.append((201,{'poll_secret':'b'*64}))
        return self.client.login()
    def test_qr_callback_pkce_and_secret_boundaries(self):
        qr=self.login();auth=dict(self.client.auth)
        self.assertEqual(qr['qr'],s.RELAY+'/s/'+auth['state'])
        relay_payload=self.http.calls[2][1]['payload']
        self.assertEqual(len(relay_payload['challenge']),43)
        self.assertNotIn('SECRET',json.dumps(relay_payload));self.assertNotIn(auth['verifier'],json.dumps(relay_payload))
        self.http.responses=[(200,{'state':auth['state'],'code':'fake-code'}),(200,{'access_token':'ACCESS'}),(200,{'ok':True})]
        self.assertTrue(self.client.poll()['authenticated'])
        exchange=self.http.calls[-2]
        self.assertEqual(exchange[0],'https://mastodon.social/oauth/token')
        self.assertEqual(exchange[1]['form']['code_verifier'],auth['verifier'])
        self.assertEqual(self.client.token,'ACCESS');self.assertIsNone(self.client.auth)
        self.assertEqual(os.stat(self.client.directory/'session.json').st_mode&0o777,0o600)
        self.assertEqual(s.Client(self.tmp.name,self.http).token,'ACCESS')
        self.assertNotIn('ACCESS',(self.client.directory/'registrations.json').read_text())
    def test_callback_wrong_state_never_exchanges(self):
        self.login();self.http.responses=[(200,{'state':'wrong','code':'bad'}),(200,{'ok':True})]
        with self.assertRaises(s.Problem):self.client.poll()
        self.assertFalse(any('/oauth/token' in url for url,_ in self.http.calls))
        self.assertEqual(self.client.token,'')
    def test_relay_failure_and_expiration_offer_manual(self):
        self.login();self.http.responses=[s.Problem('offline')]*3+[(200,{'ok':True})]
        self.assertTrue(self.client.poll()['pending']);self.assertTrue(self.client.poll()['pending']);self.assertTrue(self.client.poll()['fallback'])
        self.login();self.client.auth['expires']=time.monotonic()-1;self.http.responses=[(200,{'ok':True})]
        self.assertTrue(self.client.poll()['fallback'])
    def test_manual_token_uses_only_mastodon_and_validates_timeline(self):
        self.http.responses=[(200,[])];self.assertTrue(self.client.manual(' manual-token ')['authenticated'])
        self.assertEqual(self.http.calls[0][0],'https://mastodon.social/api/v1/timelines/home?limit=1')
        self.assertEqual(self.client.token,'manual-token')
        self.http.responses=[(200,{'error':'invalid'})]
        with self.assertRaises(s.Problem):self.client.manual('other-token')
        self.assertEqual(self.client.token,'manual-token')
        with self.assertRaises(s.Problem):self.client.manual('bad\nheader')
    def test_rate_limit_stops_retry_requests(self):
        self.http.responses=[s.Problem('rate',429,60)]
        with self.assertRaises(s.Problem):self.client.manual('token')
        with self.assertRaises(s.Problem):self.client.manual('token')
        self.assertEqual(len(self.http.calls),1)
    def test_settings_persist_private_files_and_logout(self):
        self.client.handle({'op':'save_prefs','dark':True,'large':True})
        self.client.handle({'op':'server','server':'example.social'})
        restored=s.Client(self.tmp.name,self.http)
        self.assertTrue(restored.prefs['dark']);self.assertTrue(restored.prefs['large']);self.assertEqual(restored.server,'example.social')
        self.assertEqual(os.stat(restored.directory/'preferences.json').st_mode&0o777,0o600)
        self.assertEqual(os.stat(restored.directory).st_mode&0o777,0o700)
        restored.token='private';restored.handle({'op':'logout'});self.assertEqual(restored.token,'')
    def test_invalid_server_preserves_account(self):
        self.client.token='private'
        for host in ['https://mastodon.social','mastodon.social/','mastodon.social:443','user@mastodon.social','localhost','127.0.0.1']:
            with self.assertRaises(s.Problem):self.client.handle({'op':'server','server':host})
        self.assertEqual(self.client.server,'mastodon.social');self.assertEqual(self.client.token,'private')
    def test_feed_pagination_and_html(self):
        self.client.token='private';self.http.responses=[(200,[{'id':'100','account':{'acct':'test','display_name':'Tester'},'content':'<p>Hello &amp; café</p><p>Next</p>','replies_count':2,'reblogs_count':3,'favourites_count':4}])]
        result=self.client.handle({'op':'feed','home':True,'max_id':'101'})
        self.assertEqual(result['posts'][0]['body'],'Hello & café\nNext')
        self.assertEqual([result['posts'][0][key] for key in ('replies','boosts','favourites')],[2,3,4])
        self.assertIn('max_id=101',self.http.calls[0][0]);self.assertEqual(self.http.calls[0][1]['token'],'private')
        with self.assertRaises(s.Problem):self.client.handle({'op':'feed','max_id':'101&evil=1'})
    def test_compose_constraints_and_direct_post(self):
        with self.assertRaises(s.Problem):self.client.handle({'op':'publish','text':'test'})
        self.client.token='private'
        with self.assertRaises(s.Problem):self.client.handle({'op':'publish','text':'a'*501})
        self.http.responses=[(200,{'id':'1'})]
        self.assertTrue(self.client.handle({'op':'publish','text':'Test fixture'})['published'])
        self.assertEqual(self.http.calls[0][0],'https://mastodon.social/api/v1/statuses')
    def test_saved_login_restart_logout_and_server_change(self):
        self.http.responses=[(200,[])]
        self.client.manual('device-token')
        restored=s.Client(self.tmp.name,self.http)
        self.assertTrue(restored.handle({'op':'prefs'})['authenticated'])
        self.assertEqual(restored.token,'device-token')
        self.assertEqual(os.stat(restored.directory/'session.json').st_mode&0o777,0o600)
        restored.handle({'op':'logout'})
        self.assertFalse((restored.directory/'session.json').exists())
        self.assertEqual(s.Client(self.tmp.name,self.http).token,'')
        self.http.responses=[(200,[])]
        restored.manual('other-token');restored.handle({'op':'server','server':'example.social'})
        self.assertEqual(s.Client(self.tmp.name,self.http).token,'')
    def test_search_warning_reply_and_boost_target(self):
        self.client.token='token'
        obj={'id':'88','account':{'acct':'mira@example.social','display_name':'Mira'},'visibility':'private','spoiler_text':'Sensitive','content':'<p>Hidden text</p>','reblogged':False}
        wrapper={'id':'99','reblog':obj}
        self.http.responses=[(200,{'statuses':[wrapper]})]
        post=self.client.handle({'op':'search','query':'cats & dogs'})['posts'][0]
        self.assertIn('q=cats+%26+dogs',self.http.calls[-1][0]);self.assertEqual(post['warning'],'Sensitive');self.assertEqual(post['body'],'Hidden text')
        self.assertEqual(post['target'],'88');self.assertEqual(post['visibility'],'private')
        self.http.responses=[(200,{'id':'4'})]
        self.client.handle({'op':'publish','text':'@mira@example.social hi','reply_to':'88','visibility':'private'})
        form=self.http.calls[-1][1]['form'];self.assertEqual(form['in_reply_to_id'],'88');self.assertEqual(form['visibility'],'private')
        self.http.responses=[(200,{'reblogged':True,'reblogs_count':8})]
        self.assertTrue(self.client.handle({'op':'boost','target':'88'})['boosted'])
        self.assertTrue(self.http.calls[-1][0].endswith('/statuses/88/reblog'))
        with self.assertRaises(s.Problem):self.client.handle({'op':'boost','target':'88/evil'})
        self.http.responses=[(200,{'reblogged':False,'reblogs_count':7})]
        self.client.handle({'op':'boost','target':'88','undo':True});self.assertTrue(self.http.calls[-1][0].endswith('/unreblog'))
        self.http.responses=[s.Problem('denied',403)]
        with self.assertRaisesRegex(s.Problem,'permission'):self.client.handle({'op':'search','query':'cats'})
    def test_logout_write_failure_does_not_claim_success(self):
        self.client.token='token'
        from unittest.mock import patch
        with patch.object(s.Path,'unlink',side_effect=OSError('read only')):
            with self.assertRaises(s.Problem):self.client.handle({'op':'logout'})
        self.assertEqual(self.client.token,'token')
    def test_no_redirects(self):
        self.assertIsNone(s.NoRedirect().redirect_request(None,None,302,'',{},'https://elsewhere.test'))
if __name__=='__main__':unittest.main()
