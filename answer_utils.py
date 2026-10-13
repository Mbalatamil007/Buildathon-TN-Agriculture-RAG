"""Answer-language instructions and deterministic missing-evidence replies."""
LANGUAGES = ['English + Tamil', 'English', 'Tamil']

def language_instruction(language):
    if language == 'English + Tamil':
        return ('Always produce both sections, in this order: "## English" followed by '
                '"## தமிழ்". The Tamil section must faithfully translate the English '
                'section, preserving every amount, date, eligibility condition, district '
                'scope, caveat and [S#] citation. Do not add new facts in translation.')
    if language == 'Tamil':
        return 'Reply entirely in Tamil, retaining exact numbers, GO references and [S#] citations.'
    if language == 'English':
        return 'Reply entirely in English, retaining exact numbers and [S#] citations.'
    raise ValueError('Unsupported answer language.')

def missing_answer(language, district):
    english = f'I could not find supporting information for {district} in the indexed official-source passages. This does not mean you are ineligible or that no scheme exists.'
    tamil = f'{district} மாவட்டத்திற்கான ஆதாரத் தகவல் அட்டவணைப்படுத்தப்பட்ட அரசு மூல ஆவணங்களில் கிடைக்கவில்லை. இதனால் நீங்கள் தகுதியற்றவர் என்றோ திட்டம் இல்லை என்றோ பொருள் கொள்ளக்கூடாது.'
    if language == 'English + Tamil':
        return f'## English\n{english}\n\n## தமிழ்\n{tamil}'
    return tamil if language == 'Tamil' else english
