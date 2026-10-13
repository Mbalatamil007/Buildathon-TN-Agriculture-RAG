from urllib.parse import urlencode
import streamlit as st
from config import BASE_DIR, EMBEDDING_MODEL, OPENAI_MODEL
from retriever import current_snapshot, scope_resources
from districts import ALL_DISTRICTS, DISTRICTS, district_label
from answer_utils import LANGUAGES
from rag_pipeline import create_rag_resources, ask_question, submit_feedback
from voice import transcribe_audio, read_aloud

st.set_page_config(page_title='Tamil Nadu Agriculture Assistant', page_icon='🌾', layout='wide')
banner = BASE_DIR / 'assets' / 'agriculture_banner.png'
if banner.exists():
    st.image(str(banner), use_container_width=True)
st.title('Tamil Nadu Agriculture Schemes Assistant')
st.caption('தமிழ்நாடு வேளாண்மை திட்டங்கள் • Source-backed answers with PDF citations')

@st.cache_resource(show_spinner=False)
def cached_resources(snapshot):
    return create_rag_resources(snapshot)

@st.cache_resource(show_spinner=False)
def cached_scoped_resources(snapshot, district):
    return scope_resources(cached_resources(snapshot), district)

with st.sidebar:
    logo = BASE_DIR / 'assets' / 'tn_logo.png'
    if logo.exists():
        st.image(str(logo), width=90)
    district = st.selectbox('District / மாவட்டம்', [ALL_DISTRICTS] + list(DISTRICTS), format_func=district_label)
    language = st.selectbox('Answer language / பதில் மொழி', LANGUAGES)
    st.caption(f'Embeddings: {EMBEDDING_MODEL}\nAnswer model: {OPENAI_MODEL}')
    st.caption('OpenAI processes document chunks, questions, OCR images and optional audio. Enabled LangSmith traces include questions and passages.')
    if st.button('Clear conversation / உரையாடலை அழி'):
        st.session_state['messages'] = []
        st.rerun()
    st.info('Weekly refresh requires the Windows scheduled task described in README.md.')

try:
    snapshot = str(current_snapshot())
    with st.spinner('Loading hybrid search...'):
        resources = cached_scoped_resources(snapshot, district)
    identity = (snapshot, district)
    if st.session_state.get('identity') != identity:
        st.session_state['messages'] = []
        st.session_state['identity'] = identity
    st.caption(f"Knowledge index built: {resources['created_at']} • {resources['chunk_count']} chunks")
    st.info(resources['knowledge_scope'])
    if not resources['chunk_count']:
        st.warning('No indexed passages for this district. Add verified district records and rebuild the index.')
except Exception as error:
    st.error(str(error))
    st.code('python create_faiss_db.py\npython -m streamlit run app.py')
    st.stop()

messages = st.session_state.setdefault('messages', [])

def render_sources(result):
    for source in result.get('sources', []):
        with st.expander(f"[{source['label']}] {source.get('source', '')} — PDF pages {source.get('page')}-{source.get('page_end', source.get('page'))}"):
            st.caption('Search: ' + ', '.join(source['retrieved_by']) + f" • RRF: {source['rrf_score']:.6f} (ranking, not confidence)")
            st.caption(f"District: {source.get('district', 'Not specified')} • Source date: {source.get('source_date', 'Not specified')}")
            if source.get('go_page'):
                st.caption(f"Original GO page: {source['go_page']}")
            if source.get('source_url', '').startswith('https://'):
                st.link_button('Official source', source['source_url'])
            st.write(source['text'])

for index, message in enumerate(messages):
    with st.chat_message(message['role']):
        st.markdown(message['content'])
        if message['role'] == 'assistant':
            result = message['result']
            render_sources(result)
            col1, col2 = st.columns(2)
            col1.link_button('Share on WhatsApp', 'https://wa.me/?' + urlencode({'text': message['content'][:5000]}))
            if col2.button('Read aloud', key=f'speak_{index}'):
                try:
                    message['audio'] = read_aloud(message['content'])
                except Exception as error:
                    st.warning(f'Audio failed: {error}')
            if message.get('audio'):
                st.caption('AI-generated voice; the first 4000 characters are read.')
                st.audio(message['audio'], format='audio/mp3')
            if result.get('run_id'):
                with st.form(f'feedback_{index}'):
                    rating = st.radio('Was this answer helpful?', ['Yes', 'No'], horizontal=True)
                    comment = st.text_input('Feedback (optional)', max_chars=2000)
                    if st.form_submit_button('Send feedback'):
                        try:
                            submit_feedback(result['run_id'], 1 if rating == 'Yes' else 0, comment)
                            st.success('Feedback saved.')
                        except Exception as error:
                            st.warning(f'Feedback was not saved: {error}')

with st.expander('Voice question / குரல் கேள்வி'):
    audio = st.audio_input('Record your question')
    if st.button('Transcribe recording', disabled=audio is None):
        try:
            st.session_state['voice_text'] = transcribe_audio(audio, language)
        except Exception as error:
            st.warning(f'Transcription failed: {error}')
    if st.session_state.get('voice_text'):
        edited = st.text_area('Check the transcription before asking', value=st.session_state['voice_text'], max_chars=2000)
        if st.button('Ask voice question'):
            st.session_state['pending_question'] = edited
            st.session_state.pop('voice_text', None)

question = st.chat_input('Ask about eligibility, subsidies or application steps / உங்கள் கேள்வி', max_chars=2000)
question = question or st.session_state.pop('pending_question', None)
if question:
    history = [{'role': m['role'], 'content': m['content']} for m in messages[-6:]]
    messages.append({'role': 'user', 'content': question})
    with st.chat_message('user'):
        st.write(question)
    with st.chat_message('assistant'):
        slot = st.empty()
        try:
            result = ask_question(question, resources, history, language, on_token=slot.markdown, district=district)
            messages.append({'role': 'assistant', 'content': result['answer'], 'result': result})
            st.session_state['messages'] = messages[-20:]
            st.rerun()
        except Exception as error:
            slot.error(f'Request failed: {error}')
            messages.pop()
