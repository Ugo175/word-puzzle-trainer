import http.client
from http.server import ThreadingHTTPServer
import json
import threading
import unittest
from game import Rounds, solutions
from server import Handler, MAX_REQUEST
from trainer import solve

DICTIONARY={'act','cat','tact','at','quiz','bee','be','react','trace','crate','care','race'}


class RoundTests(unittest.TestCase):
    def setUp(self):
        self.now=100.0
        self.rounds=Rounds(DICTIONARY,clock=lambda:self.now)

    def test_blank_scoring_and_shared_solver(self):
        result=solutions('qui?',DICTIONARY,2)
        self.assertEqual(result[0]['word'],'quiz')
        self.assertEqual(result[0]['score'],12)
        self.assertEqual(result[0]['tiles'][-1],{'letter':'z','points':0,'blank':True})
        core=solve('cat?',DICTIONARY)
        self.assertEqual([{k:v for k,v in item.items() if k!='tiles'} for item in solutions('cat?',DICTIONARY,1)],core)

    def test_no_solutions_revealed_before_finish(self):
        start=self.rounds.start('cat',30,2)
        self.assertNotIn('solutions',start)
        self.assertNotIn('missed',start)
        self.assertEqual(start['remaining'],30)

    def test_duplicate_and_invalid_guesses(self):
        start=self.rounds.start('cat',60,2)
        first=self.rounds.act(start['id'],'cat')
        self.assertTrue(first['accepted'])
        duplicate=self.rounds.act(start['id'],'cat')
        self.assertFalse(duplicate['accepted'])
        self.assertEqual(duplicate['score'],5)
        invalid=self.rounds.act(start['id'],'quiz')
        self.assertFalse(invalid['accepted'])
        self.assertEqual(invalid['score'],5)

    def test_deadline_rejects_late_guess(self):
        start=self.rounds.start('cat',30,2)
        self.now+=30
        late=self.rounds.act(start['id'],'cat')
        self.assertTrue(late['finished'])
        self.assertEqual(late['score'],0)
        self.assertEqual(late['found'],[])
        self.assertIn('cat',[word['word'] for word in late['missed']])

    def test_early_finish_idempotent(self):
        start=self.rounds.start('cat',60,2)
        self.rounds.act(start['id'],'act')
        finish=self.rounds.act(start['id'],finish=True)
        again=self.rounds.act(start['id'],'cat')
        self.assertTrue(again['finished'])
        self.assertEqual(finish['score'],5)
        self.assertEqual(finish['date'],again['date'])
        self.assertEqual([item['word'] for item in finish['found']],['act'])

    def test_validation_and_minimum(self):
        for rack in [None,'','123','a'*13]:
            with self.assertRaises(ValueError): solutions(rack,DICTIONARY)
        for minimum in [0,13,True,2.5,'2']:
            with self.assertRaises(ValueError): self.rounds.start('cat',60,minimum)
        for duration in [0,1,True,30.0,61]:
            with self.assertRaises(ValueError): self.rounds.start('cat',duration,2)
        with self.assertRaises(ValueError): self.rounds.start('zzz',60,2)
        with self.assertRaises(ValueError): self.rounds.act('missing','cat')
        self.assertEqual([word['word'] for word in solutions('cat',DICTIONARY,3)],['act','cat'])

    def test_round_isolation_and_expiry(self):
        one=self.rounds.start('cat',60,2)
        two=self.rounds.start('cat',60,2)
        self.rounds.act(one['id'],'cat')
        self.assertEqual(self.rounds.act(two['id'],'act')['score'],5)
        self.now+=601
        self.rounds.start('cat',60,2)
        with self.assertRaises(ValueError): self.rounds.act(one['id'],'cat')


class QuietHandler(Handler):
    def log_message(self,*args): pass


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
        cls.server.dictionary=DICTIONARY
        cls.server.rounds=Rounds(DICTIONARY)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def request(self,method,path,data=None,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        try:
            connection.request(method,path,data,headers or {})
            response=connection.getresponse()
            return response.status,dict(response.getheaders()),response.read()
        finally: connection.close()
    def post(self,path,payload):
        status,_,body=self.request('POST',path,json.dumps(payload),{'Content-Type':'application/json'})
        return status,json.loads(body)
    def test_full_round_flow(self):
        status,started=self.post('/api/round/start',{'rack':'cat','seconds':30,'minimum':2})
        self.assertEqual(status,200)
        status,guess=self.post('/api/round/guess',{'id':started['id'],'word':'cat'})
        self.assertTrue(guess['accepted'])
        status,finish=self.post('/api/round/finish',{'id':started['id']})
        self.assertEqual(status,200)
        self.assertEqual(finish['score'],5)
        self.assertEqual({word['word'] for word in finish['missed']},{'act','at'})
    def test_api_validation(self):
        for payload in [None,[],{}, {'rack':False},{'rack':'cat','minimum':False}]:
            self.assertEqual(self.post('/api/solve',payload)[0],400)
        self.assertEqual(self.post('/api/round/guess',{'word':'cat'})[0],400)
        self.assertEqual(self.request('POST','/api/solve','{',{'Content-Type':'application/json'})[0],400)
        self.assertEqual(self.request('POST','/api/solve','{}',{'Content-Type':'text/plain'})[0],415)
        self.assertEqual(self.request('POST','/api/solve',headers={'Content-Type':'application/json','Content-Length':str(MAX_REQUEST+1)})[0],413)
    def test_assets_origin_and_solver(self):
        for path in ['/','/app.js','/styles.css','/favicon.svg']:
            status,headers,body=self.request('GET',path)
            self.assertEqual(status,200);self.assertTrue(body)
            self.assertEqual(headers['X-Content-Type-Options'],'nosniff')
        self.assertEqual(self.request('GET','/trainer.py')[0],404)
        self.assertEqual(self.request('GET','/',headers={'Host':'elsewhere.test'})[0],403)
        self.assertEqual(self.request('POST','/api/solve','{}',{'Content-Type':'application/json','Origin':'https://elsewhere.test'})[0],403)
        status,result=self.post('/api/solve',{'rack':'qui?','minimum':2})
        self.assertEqual(status,200);self.assertEqual(result['words'][0]['score'],12)
