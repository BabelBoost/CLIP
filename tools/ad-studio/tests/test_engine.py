import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import StudioError, parse_srt, probe, render, text_panel

class ValidationTests(unittest.TestCase):
    def test_srt_polish_and_crlf(self):
        result=parse_srt('\ufeff1\r\n00:00:01,050 --> 00:00:02,200\r\nZażółć gęślą\r\njaźń\r\n')
        self.assertEqual(result,[{'start':1.05,'end':2.2,'text':'Zażółć gęślą\njaźń'}])
    def test_invalid_srt_rejected(self):
        for s in ['1\n00:00:04,000 --> 00:00:02,000\nText','bad','1\n00:99:00,000 --> 01:00:00,000\nText']:
            with self.assertRaises(StudioError):parse_srt(s)
    def test_literal_special_characters(self):
        panel=text_panel("50%: 'Hello' \\ {text} Żółć",600,32)
        self.assertGreater(panel.height,20)

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
class RenderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        def ff(args):
            subprocess.run(['ffmpeg','-v','error','-y',*args],check=True)
        self.silent=self.root/'a apostrophe\'s video.mp4'
        self.audio=self.root/'portrait.mp4'
        ff(['-f','lavfi','-i','color=c=blue:s=320x180:r=30','-t','1','-c:v','libx264',str(self.silent)])
        ff(['-f','lavfi','-i','color=c=green:s=180x320:r=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','1','-c:v','libx264','-c:a','aac',str(self.audio)])
        self.music=self.root/'music.wav'
        ff(['-f','lavfi','-i','sine=frequency=220:sample_rate=48000','-t','0.5',str(self.music)])
        from PIL import Image
        self.cover=self.root/'cover.png';Image.new('RGB',(200,300),'red').save(self.cover)
    def tearDown(self):self.tmp.cleanup()
    def project(self):
        return {'clips':[{'path':str(self.silent),'start':.1,'end':.6},{'path':str(self.audio),'start':0,'end':.5}],'size':[720,1280],'outro_seconds':.5,'cover':str(self.cover),'title':'Test','hook':"50%: Żółć's test",'hook_seconds':.3,'captions':parse_srt('1\n00:00:00,400 --> 00:00:00,900\nHello world'),'music':str(self.music),'voice':str(self.music),'original_volume':.2}
    def test_mixed_formats_silent_audio_music_cover_captions(self):
        output=render(self.project(),self.root/'result.mp4')
        info=probe(output)
        self.assertAlmostEqual(info['duration'],1.5,delta=.15)
        self.assertEqual((info['video']['width'],info['video']['height']),(720,1280))
        self.assertTrue(info['audio'])
    def test_bad_trim_preserves_existing_output(self):
        output=self.root/'keep.mp4';output.write_bytes(b'keep')
        p=self.project();p['clips'][0]['end']=20
        with self.assertRaises(StudioError):render(p,output)
        self.assertEqual(output.read_bytes(),b'keep')
    def test_voice_too_long_rejected(self):
        p=self.project();p['clips']=p['clips'][:1];p['outro_seconds']=0;p['voice']=str(self.audio)
        p['captions']=[]
        with self.assertRaisesRegex(StudioError,'lektor'):render(p,self.root/'result.mp4')
    def test_minimal_crop_without_overlays_or_outro(self):
        p={'clips':[{'path':str(self.silent),'start':0,'end':.3}],'size':[720,1280],'fit':'crop','outro_seconds':0}
        out=render(p,self.root/'minimal.mp4')
        self.assertAlmostEqual(probe(out)['duration'],.3,delta=.15)

if __name__=='__main__':unittest.main()
