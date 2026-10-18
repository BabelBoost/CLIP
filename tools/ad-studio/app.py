from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import uuid
import streamlit as st
from engine import StudioError, parse_srt, probe, render

st.set_page_config(page_title='Babel Boost Ad Studio',layout='wide')
st.markdown('''<style>.stApp {background:#0b1220;color:#e8eef7} h1,h2,h3 {color:#eef5ff} .block-container {max-width:1300px;padding-top:2rem} div[data-testid="stMetric"] {background:#152237;border-radius:12px;padding:16px}</style>''',unsafe_allow_html=True)
st.caption('BABEL BOOST / VIDEO TOOLS')
st.title('Ad Studio')
st.write('Zmień klipy z Grok AI i AutoShorts.ai w gotową reklamę.')
st.caption('Praca lokalna. Wczytaj pobrane pliki. Program nie loguje się do Grok ani AutoShorts i nie usuwa napisów już zapisanych w obrazie.')
if 'workspace' not in st.session_state:
    st.session_state.workspace=tempfile.TemporaryDirectory(prefix='babel-ad-studio-')
root=Path(st.session_state.workspace.name)
def save_upload(upload):
    if upload is None:
        return None
    data=upload.getvalue();digest=hashlib.sha256(data).hexdigest()
    path=root/(digest+Path(upload.name).suffix.lower())
    if not path.exists():
        path.write_bytes(data)
    return str(path)

@st.cache_data(show_spinner=False)
def metadata(path):
    return probe(path)

DEFAULTS={'hook':'Your Iceland plan looks perfect.\nUntil the weather changes.','hook_seconds':3.0,'title':'ICELAND WINTER ROAD TRIP GUIDE','cta':'GET THE EBOOK','website':'BabelBoost.com','outro_seconds':4.0,'size_name':'Pionowy 720p (szybki)','fit_name':'Cały obraz','original_volume':0.0,'music_volume':0.12,'voice_volume':1.0,'srt_text':''}
SIZES={'Pionowy 720p (szybki)':[720,1280],'Pionowy 1080p':[1080,1920],'Poziomy 1080p':[1920,1080],'Kwadrat':[1080,1080]}
for key,value in DEFAULTS.items():
    st.session_state.setdefault(key,value)
with st.sidebar:
    st.header('Projekt')
    project_file=st.file_uploader('Wczytaj zapisany projekt JSON',type=['json'])
    if st.button('Przywróć ustawienia',disabled=project_file is None):
        try:
            data=json.loads(project_file.getvalue())
            if data.get('version')!=1 or not isinstance(data.get('settings'),dict) or not isinstance(data.get('clips'),list):
                raise ValueError('Nieobsługiwany format projektu.')
            settings=data['settings']
            for key,default in DEFAULTS.items():
                value=settings.get(key,default)
                if isinstance(default,float):
                    from engine import finite
                    limits={'hook_seconds':(.1,15),'outro_seconds':(0,15),'original_volume':(0,2),'music_volume':(0,1),'voice_volume':(0,2)}
                    value=finite(value,key,*limits[key])
                elif not isinstance(value,str) or len(value)>100000:
                    raise ValueError('Niepoprawne ustawienia tekstu.')
            if settings.get('size_name',DEFAULTS['size_name']) not in SIZES or settings.get('fit_name','Cały obraz') not in ['Cały obraz','Wypełnij kadr']:
                raise ValueError('Niepoprawny format obrazu.')
            for key,default in DEFAULTS.items():
                st.session_state[key]=settings.get(key,default)
            st.session_state.restored_clips=data['clips']
            st.session_state.table_revision=st.session_state.get('table_revision',0)+1
            st.success('Ustawienia przywrócone. Wczytaj ponownie te same pliki źródłowe, muzykę i okładkę.')
        except (ValueError,TypeError,KeyError,StudioError) as exc:
            st.error(str(exc))
    st.selectbox('Format eksportu',list(SIZES),key='size_name')
    st.selectbox('Kadrowanie',['Cały obraz','Wypełnij kadr'],key='fit_name',help='Cały obraz chroni napisy i okładki. Wypełnienie przycina brzegi.')
    st.info('Jeżeli AutoShorts ma już lektora, zwiększ głośność klipów. Domyślnie jest wyciszona.')

st.subheader('1. Ujęcia i kolejność')
uploads=st.file_uploader('Dodaj klipy MP4, MOV lub WebM',type=['mp4','mov','webm','mkv'],accept_multiple_files=True)
rows=[];assets={}
for i,upload in enumerate(uploads):
    path=save_upload(upload)
    try:
        info=metadata(path)
        if not info['video'] or info['duration']<=0:
            raise StudioError('Plik nie zawiera prawidłowego filmu.')
        asset_id=Path(path).stem
        if asset_id in assets:
            st.warning(f'Pominięto powtórzony plik: {upload.name}');continue
        assets[asset_id]=path
        restored=next((c for c in st.session_state.get('restored_clips',[]) if c.get('id')==asset_id),{})
        rows.append({'Użyj':bool(restored.get('enabled',True)),'Kolejność':int(restored.get('order',i+1)),'Plik':upload.name,'Od (s)':float(restored.get('start',0)),'Do (s)':float(restored.get('end',info['duration'])),'Długość':round(info['duration'],3),'id':asset_id})
    except (StudioError,ValueError,TypeError) as exc:
        st.error(f'{upload.name}: {exc}')
if rows:
    table_key='timeline_'+hashlib.sha256(''.join(assets).encode()).hexdigest()[:12]+'_'+str(st.session_state.get('table_revision',0))
    edited=st.data_editor(rows,hide_index=True,disabled=['Plik','Długość','id'],column_config={'id':None,'Kolejność':st.column_config.NumberColumn(min_value=1,step=1),'Od (s)':st.column_config.NumberColumn(min_value=0,step=.1,format='%.2f'),'Do (s)':st.column_config.NumberColumn(min_value=.1,step=.1,format='%.2f')},key=table_key,use_container_width=True)
    with st.expander('Podgląd pliku źródłowego'):
        selected=st.selectbox('Ujęcie',list(assets),format_func=lambda key:next(r['Plik'] for r in rows if r['id']==key))
        st.video(assets[selected])
else:
    edited=[]
    st.info('Dodaj co najmniej jeden klip. Kolejność ustawisz w tabeli.')
left,right=st.columns(2)
with left:
    st.subheader('2. Hook i napisy')
    st.text_area('Hook na początku',key='hook',height=90)
    st.number_input('Czas hooka w sekundach',min_value=.1,max_value=15.0,step=.5,key='hook_seconds')
    srt=st.file_uploader('Import napisów SRT',type=['srt'])
    if st.button('Wstaw SRT do edytora',disabled=srt is None):
        try:
            st.session_state.srt_text=srt.getvalue().decode('utf-8-sig')
        except UnicodeError:
            st.error('Zapisz SRT w kodowaniu UTF-8.')
    st.text_area('Napisy SRT dla finalnej osi czasu',key='srt_text',height=180,placeholder='1\n00:00:03,000 --> 00:00:06,000\nPlan around daylight.')
    st.caption('Czasy SRT liczone są od początku zmontowanego filmu, nie od pliku źródłowego. Napisy nie są generowane automatycznie.')
with right:
    st.subheader('3. Dźwięk')
    music=st.file_uploader('Podkład muzyczny',type=['mp3','wav','m4a','ogg'],key='music_upload')
    voice=st.file_uploader('Nagranie lektora lub hooka',type=['mp3','wav','m4a','ogg'],key='voice_upload')
    st.slider('Głośność muzyki',0.0,1.0,step=.01,key='music_volume')
    st.slider('Głośność lektora',0.0,2.0,step=.05,key='voice_volume')
    st.slider('Oryginalny dźwięk klipów',0.0,2.0,step=.05,key='original_volume')
    st.caption('Lektor zaczyna od 0:00. Muzyka zapętla się do długości filmu. To import nagrania, nie generator głosu AI.')
    if voice:
        st.audio(voice)
st.subheader('4. Zakończenie reklamy')
a,b=st.columns(2)
with a:
    cover=st.file_uploader('Okładka ebooka PNG lub JPG',type=['png','jpg','jpeg'])
    if cover:
        st.image(cover,width=160)
with b:
    st.text_input('Tytuł',key='title')
    st.text_input('Wezwanie do działania',key='cta')
    st.text_input('Adres sklepu',key='website')
    st.number_input('Czas zakończenia (0 wyłącza)',min_value=0.0,max_value=15.0,step=.5,key='outro_seconds')
try:
    chosen=sorted([r for r in edited if r['Użyj']],key=lambda r:int(r['Kolejność']))
    duration=sum(float(r['Do (s)'])-float(r['Od (s)']) for r in chosen)+st.session_state.outro_seconds
    valid=bool(chosen) and all(0<=float(r['Od (s)'])<float(r['Do (s)'])<=float(next(x['Długość'] for x in rows if x['id']==r['id']))+.002 for r in chosen)
except (ValueError,TypeError):
    chosen=[];duration=0;valid=False
c1,c2,c3=st.columns(3)
c1.metric('Ujęcia',len(chosen));c2.metric('Długość',f'{duration:.1f} s');c3.metric('Format',st.session_state.size_name)
if chosen and not valid:
    st.error('Popraw czasy przycięcia w tabeli.')
settings={key:st.session_state[key] for key in DEFAULTS}
manifest={'version':1,'settings':settings,'clips':[{'id':r['id'],'name':r['Plik'],'enabled':r['Użyj'],'order':r['Kolejność'],'start':r['Od (s)'],'end':r['Do (s)']} for r in edited]}
st.download_button('Zapisz projekt JSON',json.dumps(manifest,ensure_ascii=False,indent=2),'babel-boost-project.json','application/json')
st.caption('JSON zawiera ustawienia i identyfikatory plików, bez filmów i nagrań. Zachowaj oryginały osobno.')
if st.button('Zmontuj i eksportuj MP4',type='primary',disabled=not valid,use_container_width=True):
    st.session_state.pop('result',None)
    try:
        project={**settings,'clips':[{'path':assets[r['id']],'start':r['Od (s)'],'end':r['Do (s)']} for r in chosen],'size':SIZES[settings['size_name']],'fit':'contain' if settings['fit_name']=='Cały obraz' else 'crop','captions':parse_srt(settings['srt_text']),'music':save_upload(music),'voice':save_upload(voice),'cover':save_upload(cover)}
        progress=st.progress(0,text='Przygotowanie')
        result=render(project,root/f'export-{uuid.uuid4().hex}.mp4',lambda n,label:progress.progress(n,text=label))
        st.session_state.result=str(result)
        st.success('Film gotowy. Pobierz go, zanim zamkniesz program.')
    except (StudioError,OSError,ValueError,KeyError) as exc:
        st.error(str(exc))
if st.session_state.get('result'):
    st.caption('Ostatni eksport. Po zmianie ustawień uruchom eksport ponownie.')
    st.video(st.session_state.result)
    with open(st.session_state.result,'rb') as f:
        st.download_button('Pobierz reklamę MP4',f,'BabelBoost_Ad.mp4','video/mp4',use_container_width=True)
