"""
Qualix AI — Domain-Structured Local Language AI Explanation Engine
Provides structured AI diagnostic explanations and executive risk advice adapted into 11 languages with business terminology.
"""

from typing import Dict, Any, List, Optional

SUPPORTED_LANGUAGES = {
    "English": {"code": "en", "flag": "🇬🇧", "native": "English"},
    "Hindi": {"code": "hi", "flag": "🇮🇳", "native": "हिन्दी"},
    "Tamil": {"code": "ta", "flag": "🇮🇳", "native": "தமிழ்"},
    "Telugu": {"code": "te", "flag": "🇮🇳", "native": "తెలుగు"},
    "Kannada": {"code": "kn", "flag": "🇮🇳", "native": "ಕನ್ನಡ"},
    "Bengali": {"code": "bn", "flag": "🇮🇳", "native": "বাংলা"},
    "Marathi": {"code": "mr", "flag": "🇮🇳", "native": "मराठी"},
    "Gujarati": {"code": "gu", "flag": "🇮🇳", "native": "ગુજરાતી"},
    "Spanish": {"code": "es", "flag": "🇪🇸", "native": "Español"},
    "French": {"code": "fr", "flag": "🇫🇷", "native": "Français"},
    "German": {"code": "de", "flag": "🇩🇪", "native": "Deutsch"}
}

# Domain template translations structured around 4 pillars:
# 1. Finding (Technical observation)
# 2. Business Meaning (Impact on MSME operations & cashflow)
# 3. Technical Explanation (Root cause)
# 4. Recommended Fix (Actionable step)

LOCALIZED_EXPLANATIONS_DB = {
    "missing_contacts": {
        "English": {
            "finding": "Customer phone numbers contain 18% missing or blank values.",
            "business_meaning": "Reduces accuracy of customer communication, SMS payment reminders, and duplicate customer identification, risking revenue leaks.",
            "technical_explanation": "Null or empty strings detected in 'Phone' / 'Contact' column across 182 rows during profile scan.",
            "recommended_fix": "Apply default fallback placeholders, extract missing numbers from Tally ledger notes, or prompt sales reps for missing contacts."
        },
        "Hindi": {
            "finding": "ग्राहक फोन नंबर में 18% डेटा उपलब्ध नहीं (खाली) है।",
            "business_meaning": "ग्राहक संचार, SMS भुगतान अनुस्मारक और डुप्लिकेट ग्राहक पहचान में बाधा आती है, जिससे राजस्व का नुकसान हो सकता है।",
            "technical_explanation": "प्रोफाइल स्कैन के दौरान 182 पंक्तियों के 'फोन/संपर्क' कॉलम में शून्य (Null) मान पाए गए।",
            "recommended_fix": "डिफ़ॉल्ट फॉलबैक मान लागू करें, टेली (Tally) लेजर नोट्स से छूटे हुए नंबर निकालें, या बिक्री प्रतिनिधि को अपडेट करने का निर्देश दें।"
        },
        "Tamil": {
            "finding": "வாடிக்கையாளர் தொலைபேசி எண்களில் 18% விடுபட்டுள்ளன.",
            "business_meaning": "வாடிக்கையாளர் தொடர்பு, SMS கட்டண நினைவூட்டல்கள் மற்றும் வாடிக்கையாளர் நகல் கண்டறிதலின் துல்லியத்தை குறைக்கிறது.",
            "technical_explanation": "182 வரிகளில் 'தொலைபேசி' நெடுவரிசையில் காலியாக உள்ள மதிப்புகள் கண்டறியப்பட்டன.",
            "recommended_fix": "Tally குறிப்புகளிலிருந்து விடுபட்ட எண்களை எடுக்கவும் அல்லது விற்பனைப் பிரதிநிதிகள் மூலம் புதுப்பிக்கவும்."
        },
        "Telugu": {
            "finding": "ఖాతాదారుల ఫోన్ నంబర్లలో 18% ఖాళీగా ఉన్నాయి.",
            "business_meaning": "కస్టమర్ కమ్యూనికేషన్ మరియు SMS చెల్లింపు రిమైండర్ల ఖచ్చితత్వాన్ని తగ్గిస్తుంది.",
            "technical_explanation": "ప్రొఫైల్ స్కాన్ సమయంలో 182 వరుసలలో ఖాళీ విలువలు కనుగొనబడ్డాయి.",
            "recommended_fix": "Tally లెడ్జర్ నుండి మిస్సింగ్ నంబర్లను సేకరించండి లేదా రికార్డులను సవరించండి."
        },
        "Kannada": {
            "finding": "ಗ್ರಾಹಕರ ದೂರವಾಣಿ ಸಂಖ್ಯೆಗಳಲ್ಲಿ 18% ಖಾಲಿ ಇವೆ.",
            "business_meaning": "ಗ್ರಾಹಕರ ಸಂಪರ್ಕ ಮತ್ತು SMS ಪಾವತಿ ನೆನಪೋಲೆಗಳ ನಿಖರತೆಯನ್ನು ಕಡಿಮೆ ಮಾಡುತ್ತದೆ.",
            "technical_explanation": "182 ಸಾಲುಗಳಲ್ಲಿ 'ಫೋನ್' ಅಂಕಣದಲ್ಲಿ ಶೂನ್ಯ ಮೌಲ್ಯಗಳು ಕಂಡುಬಂದಿವೆ.",
            "recommended_fix": "ಟ್ಯಾಲಿ (Tally) ಲೆಡ್ಜರ್ ಟಿಪ್ಪಣಿಗಳಿಂದ ಸಂಖ್ಯೆಗಳನ್ನು ಪಡೆದುಕೊಳ್ಳಿ ಅಥವಾ ನವೀಕರಿಸಿ."
        },
        "Bengali": {
            "finding": "গ্রাহকের ফোন নম্বরে ১৮% খালি তথ্য রয়েছে।",
            "business_meaning": "গ্রাহক যোগাযোগ এবং SMS পেমেন্ট রিমাইন্ডারের নির্ভুলতা হ্রাস করে।",
            "technical_explanation": "১৮২টি সারিতে ফোন নম্বর কলামে শুন্য মান পাওয়া গেছে।",
            "recommended_fix": "ট্যালি লেজার থেকে সঠিক নম্বর সংগ্রহ করুন অথবা ডিফল্ট সেট করুন।"
        },
        "Marathi": {
            "finding": "ग्राहक फोन नंबरमध्ये 18% डेटा उपलब्ध नाही (रिक्त आहे).",
            "business_meaning": "ग्राहक संवाद आणि SMS पेमेंट स्मरणपत्रांची अचूकता कमी होते, ज्यामुळे महसुलाचे नुकसान होऊ शकते.",
            "technical_explanation": "प्रोफाईल स्कॅन दरम्यान 182 पंक्तींमध्ये 'फोन' कॉलममध्ये शून्य (Null) मूल्ये आढळली.",
            "recommended_fix": "टॅली (Tally) लेजर नोट्समधून उर्वरित नंबर मिळवा किंवा सेल्स टीमला अपडेट करण्यास सांगा."
        },
        "Gujarati": {
            "finding": "ગ્રાહક ફોન નંબરમાં 18% ખાલી મૂલ્યો છે.",
            "business_meaning": "ગ્રાહક સંપર્ક અને SMS પેમેન્ટ રિમાઇન્ડરની સચોટતા ઘટે છે.",
            "technical_explanation": "182 લાઇનના ફોન કૉલમમાં ખાલી જગ્યાઓ મળી આવી છે.",
            "recommended_fix": "ટેલી (Tally) લેજરમાંથી નંબર મેળવો અથવા સેલ્સ ટીમને અપડેટ કરવા જણાવો."
        },
        "Spanish": {
            "finding": "El 18% de los números de teléfono de clientes están en blanco.",
            "business_meaning": "Reduce la precisión de recordatorios de cobro por SMS y detección de clientes duplicados.",
            "technical_explanation": "Valores nulos detectados en la columna 'Teléfono' en 182 filas.",
            "recommended_fix": "Establecer valores predeterminados o extraer números faltantes desde registros contables."
        },
        "French": {
            "finding": "18% des numéros de téléphone clients sont absents.",
            "business_meaning": "Réduit l'efficacité des rappels de paiement et la détection des doublons.",
            "technical_explanation": "Valeurs nulles détectées dans la colonne 'Téléphone' sur 182 lignes.",
            "recommended_fix": "Appliquer des valeurs par défaut ou mettre à jour les fiches clients."
        },
        "German": {
            "finding": "18% der Kunden-Telefonnummern fehlen.",
            "business_meaning": "Beeinträchtigt die Genauigkeit von SMS-Zahlungserinnerungen und Kundenzuordnungen.",
            "technical_explanation": "Nullwerte in der Spalte 'Telefon' bei 182 Datensätzen gefunden.",
            "recommended_fix": "Standardwerte setzen oder Kontaktdaten aus Buchhaltungsunterlagen ergänzen."
        }
    },
    "duplicate_vendors": {
        "English": {
            "finding": "Fuzzy duplicate detection flagged 24 supplier name variations.",
            "business_meaning": "Splits purchase order history across multiple vendor IDs, hindering bulk discount negotiations and causing double payouts.",
            "technical_explanation": "RapidFuzz similarity ratio > 88% detected between entries such as 'Reliable Logistics Private Limited' and 'RELIABLE LOGISTICS PVT LTD'.",
            "recommended_fix": "Run automated Entity Resolution in Qualix Fix Center to merge duplicate accounts into a unified Master Vendor ID."
        },
        "Hindi": {
            "finding": "फजी डुप्लिकेट पहचान ने 24 आपूर्तिकर्ता (Vendor) नाम भिन्नताओं को चिह्नित किया।",
            "business_meaning": "खरीद इतिहास कई वेंडर आईडी में विभाजित हो जाता है, जिससे छूट वार्ता में बाधा आती है और दोहरे भुगतान का जोखिम रहता है।",
            "technical_explanation": "'Reliable Logistics Private Limited' और 'RELIABLE LOGISTICS PVT LTD' के बीच RapidFuzz समानता अनुपात > 88% पाया गया।",
            "recommended_fix": "क्वालिक्स फिक्स सेंटर (Qualix Fix Center) में स्वचालित एंटिटी रिज़ॉल्यूशन चलाकर खाते एकीकृत करें।"
        },
        "Tamil": {
            "finding": "24 விநியோகஸ்தர் பெயர்களில் நகல்கள் கண்டறியப்பட்டுள்ளன.",
            "business_meaning": "கொள்முதல் வரலாற்றைப் பிரித்து, மொத்த தள்ளுபடி பேச்சுவார்த்தைகளை பாதிக்கிறது மற்றும் இரட்டைப் பணப்பரிமாற்ற அபாயத்தை உருவாக்குகிறது.",
            "technical_explanation": "'Reliable Logistics Pvt Ltd' மற்றும் பெயர்களுக்கு இடையே RapidFuzz 88% ஒத்தப்பாடு கண்டறியப்பட்டது.",
            "recommended_fix": "Qualix Fix Center மூலம் கணக்குகளை ஒரே முதன்மை கணக்காக இணைக்கவும்."
        },
        "Telugu": {
            "finding": "24 సప్లయర్ పేర్లలో నకిలీ వ్యత్యాసాలు కనుగొనబడ్డాయి.",
            "business_meaning": "కొనుగోలు చరిత్రను విభజించి, రాయితీ చర్చలను దెబ్బతీస్తుంది.",
            "technical_explanation": "RapidFuzz పోలిక శాతం > 88% నమోదు చేయబడింది.",
            "recommended_fix": "Qualix Fix Center లో ఎంటిటీ రిజల్యూషన్ ద్వారా విలీనం చేయండి."
        },
        "Kannada": {
            "finding": "24 ಪೂರೈಕೆದಾರರ ಹೆಸರುಗಳಲ್ಲಿ ನಕಲಿ ವ್ಯತ್ಯಾಸಗಳು ಕಂಡುಬಂದಿವೆ.",
            "business_meaning": "ಖರೀದಿ ಇತಿಹಾಸವನ್ನು ವಿಂಗಡಿಸಿ, ರಿಯಾಯಿತಿ ಸಂಭಾಷಣೆಗಳನ್ನು ಬಾಧಿಸುತ್ತದೆ.",
            "technical_explanation": "RapidFuzz ಸಾಮ್ಯತೆ 88% ಕ್ಕಿಂತ ಹೆಚ್ಚಾಗಿದೆ.",
            "recommended_fix": "Qualix Fix Center ಮೂಲಕ ಖಾತೆಗಳನ್ನು ವಿಲೀನಗೊಳಿಸಿ."
        },
        "Bengali": {
            "finding": "২৪টি সরবরাহকারী নামে সদৃশ মান চিহ্নিত হয়েছে।",
            "business_meaning": "ক্রয় হিস্ট্রি আলাদা হয়ে যায় এবং ডাবল পেমেন্টের ঝুঁকি তৈরি হয়।",
            "technical_explanation": "RapidFuzz সিমিলারিটি স্কোর ৮৮% এর বেশি পাওয়া গেছে।",
            "recommended_fix": "Qualix Fix Center-এ অটোমেটেড অ্যান্টিটি রেজোলিউশন চালান।"
        },
        "Marathi": {
            "finding": "24 पुरवठादार (Vendor) नावांमध्ये डुप्लिकेट तफावत आढळली.",
            "business_meaning": "खरेदी इतिहास वेगवेगळ्या वेंडर आयडीमध्ये विभागला जातो, ज्यामुळे सवलत वाटाघाटीत अडथळा येतो.",
            "technical_explanation": "'Reliable Logistics Pvt Ltd' सारख्या नोंदींमध्ये RapidFuzz साम्य > 88% आढळले.",
            "recommended_fix": "Qualix Fix Center मध्ये एंटिटी रिझोल्यूशन वापरून खाती एकत्रित करा."
        },
        "Gujarati": {
            "finding": "24 સપ્લાયર નામોમાં ડુપ્લિકેટ ભિન્નતા મળી આવી.",
            "business_meaning": "ખરીદીનો ઇતિહાસ અલગ-અલગ આઈડીમાં વહેંચાઈ જાય છે.",
            "technical_explanation": "RapidFuzz સમાનતા દર 88% થી વધુ નોંધાયો છે.",
            "recommended_fix": "Qualix Fix Center દ્વારા મર્જ કરો."
        },
        "Spanish": {
            "finding": "Se detectaron 24 variaciones de nombres de proveedores duplicados.",
            "business_meaning": "Fragmenta el historial de compras y dificulta la negociación de descuentos por volumen.",
            "technical_explanation": "Similitud RapidFuzz > 88% entre registros de proveedores.",
            "recommended_fix": "Ejecutar la resolución de entidades en Qualix Fix Center para unificar cuentas."
        },
        "French": {
            "finding": "24 variations de noms de fournisseurs en double détectées.",
            "business_meaning": "Fragmente l'historique d'achat et risque d'entraîner des doubles paiements.",
            "technical_explanation": "Ratio de similarité RapidFuzz > 88% identifié.",
            "recommended_fix": "Fusionner les fiches fournisseurs via le centre de correction Qualix."
        },
        "German": {
            "finding": "24 doppelte Lieferantennamen mit geringen Abweichungen erkannt.",
            "business_meaning": "Teilt die Einkaufshistorie auf mehrere Konten auf und erschwert Rabattverhandlungen.",
            "technical_explanation": "RapidFuzz-Ähnlichkeitsrate > 88% festgestellt.",
            "recommended_fix": "Entitäten-Zusammenführung im Qualix Fix Center ausführen."
        }
    },
    "schema_drift_warning": {
        "English": {
            "finding": "Schema Drift detected: Column 'GST_No' missing, substituted by 'Tax_ID'.",
            "business_meaning": "Causes integration pipeline failures during automated GST return compilation and ERP sync.",
            "technical_explanation": "Expected target schema key 'GST_No' was not found in ingested file stream; fuzzy matched to 'Tax_ID'.",
            "recommended_fix": "Approve schema mapping template in Schema & Rules manager or update automated column alias rule."
        },
        "Hindi": {
            "finding": "स्कीमा ड्रिफ्ट पहचान: 'GST_No' कॉलम गायब है, इसकी जगह 'Tax_ID' आया है।",
            "business_meaning": "स्वचालित जीएसटी रिटर्न संकलन और ईआरपी सिंक के दौरान एकीकरण में त्रुटि आती है।",
            "technical_explanation": "अपलोड की गई फाइल में 'GST_No' कॉलम नहीं मिला; इसे 'Tax_ID' से मैप किया गया।",
            "recommended_fix": "स्कीमा एवं नियम (Schema & Rules) प्रबंधक में मैपिंग टेम्पलेट को स्वीकृत करें।"
        },
        "Tamil": {
            "finding": "ஸ்கீமா மாற்றம்: 'GST_No' நெடுவரிசை விடுபட்டு 'Tax_ID' என மாறியுள்ளது.",
            "business_meaning": "தானியங்கி GST தாக்கல் மற்றும் ERP ஒத்திசைவில் பிழைகளை ஏற்படுத்துகிறது.",
            "technical_explanation": "எதிர்பார்க்கப்பட்ட 'GST_No' நெடுவரிசைக்கு பதிலாக 'Tax_ID' கண்டுபிடிக்கப்பட்டது.",
            "recommended_fix": "Schema & Rules பிரிவில் மேப்பிங்கை உறுதிப்படுத்தவும்."
        },
        "Telugu": {
            "finding": "స్కీమా డ్రిఫ్ట్ గుర్తించబడింది: 'GST_No' లేక 'Tax_ID' గా ఉంది.",
            "business_meaning": "GST రిటర్న్లు మరియు ERP సింక్‌లో అంతరాయం కలిగిస్తుంది.",
            "technical_explanation": "ఆశించిన కాలమ్ పేరు మారినందున డ్రిఫ్ట్ ఫ్లాగ్ చేయబడింది.",
            "recommended_fix": "Schema & Rules మ్యాపింగ్ ఆమోదించండి."
        },
        "Kannada": {
            "finding": "ಸ್ಕೀಮಾ ಬದಲಾವಣೆ: 'GST_No' ಅಂಕಣದ ಬದಲಿಗೆ 'Tax_ID' ಬಂದಿದೆ.",
            "business_meaning": "ಜಿಎಸ್‌ಟಿ ರಿಟರ್ನ್ಸ್ ಮತ್ತು ಇಆರ್‌ಪಿ ಸಿಂಕ್ ವ್ಯವಸ್ಥೆಯಲ್ಲಿ ಅಡಚಣೆ ಉಂಟುಮಾಡುತ್ತದೆ.",
            "technical_explanation": "'GST_No' ಬದಲಿಗೆ 'Tax_ID' ಹೊಂದಾಣಿಕೆ ಮಾಡಲಾಗಿದೆ.",
            "recommended_fix": "Schema & Rules ವಿಭಾಗದಲ್ಲಿ ಮ್ಯಾಪಿಂಗ್ ದೃಢೀಕರಿಸಿ."
        },
        "Bengali": {
            "finding": "স্কিমা ড্রাফট সংকেত: 'GST_No' কলামের বদলে 'Tax_ID' পাওয়া গেছে।",
            "business_meaning": "স্বয়ংক্রিয় জিএসটি রিটার্ন এবং ইআরপি সিংকে সমস্যা তৈরি করে।",
            "technical_explanation": "প্রত্যাশিত কলাম নামটি পরিবর্তিত দেখা গেছে।",
            "recommended_fix": "Schema & Rules ম্যাপিং অনুমোদন করুন।"
        },
        "Marathi": {
            "finding": "स्कीमा बदल आढळला: 'GST_No' कॉलमऐवजी 'Tax_ID' आले आहे.",
            "business_meaning": "ऑटोमेटेड जीएसटी रिटर्न आणि ईआरपी सिंकदरम्यान त्रुटी निर्माण होतात.",
            "technical_explanation": "अपेक्षित 'GST_No' ऐवजी 'Tax_ID' कॉलम मॅप झाला आहे.",
            "recommended_fix": "Schema & Rules मॅनेजरमध्ये मॅपिंग टेम्पलेट मंजूर करा."
        },
        "Gujarati": {
            "finding": "સ્કીમા ડ્રિફ્ટ: 'GST_No' ને બદલે 'Tax_ID' કૉલમ મળ્યો.",
            "business_meaning": "GST રિટર્ન અને ERP સિંકમાં સમસ્યા થાય છે.",
            "technical_explanation": "અપેક્ષિત કોલમ નામ બદલાયેલું છે.",
            "recommended_fix": "Schema & Rules મંજૂર કરો."
        },
        "Spanish": {
            "finding": "Cambio de esquema detectado: Falta la columna 'GST_No', reemplazada por 'Tax_ID'.",
            "business_meaning": "Provoca fallos en la integración con sistemas ERP y declaraciones fiscales.",
            "technical_explanation": "Columna 'GST_No' no encontrada, asignada automáticamente a 'Tax_ID'.",
            "recommended_fix": "Aprobar la plantilla de asignación en el gestor de Esquema y Reglas."
        },
        "French": {
            "finding": "Dérive de schéma détectée : Colonne 'GST_No' remplacée par 'Tax_ID'.",
            "business_meaning": "Provoque des erreurs d'intégration ERP et d'exportation fiscale.",
            "technical_explanation": "Clé de schéma attendue non trouvée ; correspondance avec 'Tax_ID'.",
            "recommended_fix": "Valider la règle de correspondance dans le gestionnaire de Schémas."
        },
        "German": {
            "finding": "Schema-Abweichung erkannt: Spalte 'GST_No' durch 'Tax_ID' ersetzt.",
            "business_meaning": "Führt zu Fehlern bei automatisierten ERP-Synchronisierungen und Steuerdaten.",
            "technical_explanation": "Erwartete Spalte fehlt; Zuordnung zu 'Tax_ID' hergestellt.",
            "recommended_fix": "Zuordnungsvorlage im Schema & Regeln Manager bestätigen."
        }
    }
}

def get_supported_languages() -> Dict[str, Dict[str, str]]:
    """Returns supported language metadata list."""
    return SUPPORTED_LANGUAGES

def explain_in_language(
    finding_key: str = "missing_contacts",
    target_language: str = "English",
    custom_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generates structured AI explanation across 4 core pillars:
    - Finding
    - Business Meaning
    - Technical Explanation
    - Recommended Fix
    Adapted to the target language with domain business terminology.
    """
    if target_language not in SUPPORTED_LANGUAGES:
        target_language = "English"

    category_db = LOCALIZED_EXPLANATIONS_DB.get(finding_key, LOCALIZED_EXPLANATIONS_DB["missing_contacts"])
    explanation = category_db.get(target_language, category_db["English"])

    if custom_context:
        formatted = {}
        for key, text in explanation.items():
            try:
                formatted[key] = text.format(**custom_context)
            except Exception:
                formatted[key] = text
        explanation = formatted

    lang_info = SUPPORTED_LANGUAGES.get(target_language, SUPPORTED_LANGUAGES["English"])

    return {
        "finding_key": finding_key,
        "language": target_language,
        "language_code": lang_info["code"],
        "flag": lang_info["flag"],
        "native_name": lang_info["native"],
        "pillars": {
            "finding": explanation["finding"],
            "business_meaning": explanation["business_meaning"],
            "technical_explanation": explanation["technical_explanation"],
            "recommended_fix": explanation["recommended_fix"]
        }
    }
