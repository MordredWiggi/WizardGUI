from __future__ import annotations

LANGUAGE_NAMES: dict[str, str] = {
    "de": "Deutsch",
    "en": "English",
    "fr": "Français",
    "hi": "हिंदी",
}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # Nav
        "nav_home": "Home",
        "nav_leaderboard": "Leaderboard",
        "nav_feedback": "Feedback",
        
        # Hero
        "hero_badge": "Wizard Score Tracker",
        "hero_title_1": "Every trick.",
        "hero_title_2": "Every triumph.",
        "hero_desc": "Score your Wizard card-game nights automatically, settle every bid dispute, and watch your group climb a living global leaderboard — trick by trick, streak by streak.",
        "cta_windows": "Download for Windows (.exe)",
        "cta_leaderboard": "View Leaderboard →",
        "cta_patreon": "Support us on Patreon",
        "cta_appstore": "Download on the App Store",
        "cta_playstore": "Get it on Google Play",
        "cta_github": "View source on GitHub",
        "coming_soon": "Coming soon",
        
        # Features
        "feat_1_title": "Automatic scoring",
        "feat_1_desc": "Enter bids and tricks — the app handles the math for every round, standard or multiplicative.",
        "feat_2_title": "Global leaderboard",
        "feat_2_desc": "Win rates, streaks, hit rates and highscores — see how your table stacks up worldwide.",
        "feat_3_title": "Private groups",
        "feat_3_desc": "Share a 4-digit code with your crew and keep a private leaderboard for your regular game nights.",
        
        # Footer
        "footer_text": "Wizard Score Tracker",
        
        # Leaderboard specific (assuming minimal)
        "leaderboard_title": "Global Leaderboard",
        "leaderboard_desc": "See the best Wizard players from around the world.",
        "lb_name": "Player",
        "lb_score": "Score",
        
        # Feedback specific
        "feedback_title": "Feedback & Ideas",
        "feedback_desc": "Got a great idea? Found a bug? Let us know below.",
        
        # Leaderboard tabs/sort
        "lb_tab_standard": "Standard",
        "lb_tab_mult": "Multiplicative (×)",
        "lb_sort_wins": "Wins",
        "lb_sort_winrate": "Win Rate",
        "lb_sort_avg": "Ø Score",
        "lb_sort_hitrate": "Hit Rate",
        "lb_sort_high": "Highscore",
        "lb_sort_streak": "Win Streak",
        "lb_loading": "Loading data...",
        "lb_global": "GLOBAL RANKINGS",
        "lb_error": "Error loading data.",
        "lb_empty": "No games in this mode yet.",
        "lb_table_games": "Games",
        "lb_table_wins": "Wins",
        "lb_table_quote": "Win Rate",
        "lb_table_avg": "Ø Score",
        "lb_table_hit": "Hit Rate",
        "lb_table_high": "Highscore",
        "lb_table_streak": "Streak",
        
        # Feedback
        "fb_submit": "Submit Feedback",
        "fb_placeholder": "Write your feedback...",

        # Groups leaderboard page
        "lb_group_global_subtitle": "GROUPS RANKING",
        "lb_group_subtitle": "GROUP PLAYER RANKING",
        "lb_search_placeholder": "Search groups by name…",
        "lb_col_group": "Group",
        "lb_players_short": "Players",
        "lb_click_group_hint": "Click a group to open its player leaderboard (4-digit code required).",
        "lb_no_groups_found": "No groups match your search.",
        "lb_hidden_badge": "HIDDEN",
        "lb_enter_code": "Enter group code",
        "lb_enter_code_for": "Enter the 4-digit code for {name}",
        "lb_open_btn": "Open",
        "lb_code_format_error": "Code must be 4 digits.",
        "lb_code_wrong": "Wrong or unknown code.",
        "lb_back_to_groups": "Back to groups",
        "cancel": "Cancel",
    },
    "de": {
        # Nav
        "nav_home": "Startseite",
        "nav_leaderboard": "Bestenliste",
        "nav_feedback": "Feedback",
        
        # Hero
        "hero_badge": "Wizard Punkte-Tracker",
        "hero_title_1": "Jeder Stich.",
        "hero_title_2": "Jeder Triumph.",
        "hero_desc": "Werte deine Wizard-Abende automatisch aus, kläre jede Stich-Diskussion und schau deiner Gruppe dabei zu, wie sie die globale Bestenliste erklimmt — Stich für Stich, Serie für Serie.",
        "cta_windows": "Download für Windows (.exe)",
        "cta_leaderboard": "Zur Bestenliste →",
        "cta_patreon": "Unterstütze uns auf Patreon",
        "cta_appstore": "Laden im App Store",
        "cta_playstore": "Jetzt bei Google Play",
        "cta_github": "Quellcode auf GitHub",
        "coming_soon": "Bald verfügbar",
        
        # Features
        "feat_1_title": "Automatische Wertung",
        "feat_1_desc": "Gib Ansagen und Stiche ein — die App übernimmt die Rechnung für jede Runde, ob Standard oder Multiplikator.",
        "feat_2_title": "Globale Bestenliste",
        "feat_2_desc": "Siegquoten, Serien, Trefferquoten und Highscores — sieh, wie dein Tisch weltweit abschneidet.",
        "feat_3_title": "Private Gruppen",
        "feat_3_desc": "Teile einen 4-stelligen Code mit deiner Crew für eine private Bestenliste.",
        
        # Footer
        "footer_text": "Wizard Punkte-Tracker",
        
        # Leaderboard specific
        "leaderboard_title": "Globale Bestenliste",
        "leaderboard_desc": "Sieh dir die besten Wizard-Spieler der Welt an.",
        "lb_name": "Spieler",
        "lb_score": "Punkte",
        
        # Feedback specific
        "feedback_title": "Feedback & Ideen",
        "feedback_desc": "Tolle Idee? Bug gefunden? Lass es uns hier wissen.",
        
        "lb_tab_standard": "Standard",
        "lb_tab_mult": "Multiplikativ (×)",
        "lb_sort_wins": "Siege",
        "lb_sort_winrate": "Gewinnquote",
        "lb_sort_avg": "Ø Punkte",
        "lb_sort_hitrate": "Trefferquote",
        "lb_sort_high": "Highscore",
        "lb_sort_streak": "Siegesserie",
        "lb_loading": "Lade Daten…",
        "lb_global": "GLOBAL RANKINGS",
        "lb_error": "Fehler beim Laden der Daten.",
        "lb_empty": "Noch keine Spiele in diesem Modus.",
        "lb_table_games": "Spiele",
        "lb_table_wins": "Siege",
        "lb_table_quote": "Quote",
        "lb_table_avg": "Ø Punkte",
        "lb_table_hit": "Treffer",
        "lb_table_high": "Highscore",
        "lb_table_streak": "Serie",
        
        "fb_submit": "Senden",
        "fb_placeholder": "Dein Feedback...",

        # Groups leaderboard page
        "lb_group_global_subtitle": "GRUPPEN-RANGLISTE",
        "lb_group_subtitle": "SPIELER-RANGLISTE DER GRUPPE",
        "lb_search_placeholder": "Gruppe nach Name suchen…",
        "lb_col_group": "Gruppe",
        "lb_players_short": "Spieler",
        "lb_click_group_hint": "Klicke eine Gruppe an, um die Spieler-Rangliste zu öffnen (4-stelliger Code nötig).",
        "lb_no_groups_found": "Keine Gruppe gefunden.",
        "lb_hidden_badge": "VERSTECKT",
        "lb_enter_code": "Gruppen-Code eingeben",
        "lb_enter_code_for": "Gib den 4-stelligen Code für {name} ein",
        "lb_open_btn": "Öffnen",
        "lb_code_format_error": "Code muss aus 4 Ziffern bestehen.",
        "lb_code_wrong": "Code falsch oder unbekannt.",
        "lb_back_to_groups": "Zurück zu den Gruppen",
        "cancel": "Abbrechen",
    },
    "fr": {
        # Nav
        "nav_home": "Accueil",
        "nav_leaderboard": "Classement",
        "nav_feedback": "Retour",
        
        # Hero
        "hero_badge": "Suivi de Score Wizard",
        "hero_title_1": "Chaque pli.",
        "hero_title_2": "Chaque triomphe.",
        "hero_desc": "Calculez automatiquement les scores de vos soirées Wizard, réglez chaque litige et regardez votre groupe gravir le classement mondial — pli par pli.",
        "cta_windows": "Télécharger pour Windows (.exe)",
        "cta_leaderboard": "Voir le classement →",
        "cta_patreon": "Soutenez-nous sur Patreon",
        "cta_appstore": "Télécharger dans l'App Store",
        "cta_playstore": "Disponible sur Google Play",
        "cta_github": "Code source sur GitHub",
        "coming_soon": "Bientôt disponible",
        
        # Features
        "feat_1_title": "Calcul automatique",
        "feat_1_desc": "Saisissez les annonces et les plis — l'application s'occupe des maths pour chaque manche.",
        "feat_2_title": "Classement mondial",
        "feat_2_desc": "Taux de victoire, séries et records — comparez votre table au reste du monde.",
        "feat_3_title": "Groupes privés",
        "feat_3_desc": "Partagez un code à 4 chiffres avec votre groupe pour un classement privé.",
        
        # Footer
        "footer_text": "Suivi de Score Wizard",
        
        "leaderboard_title": "Classement mondial",
        "leaderboard_desc": "Voyez les meilleurs joueurs de Wizard du monde entier.",
        "lb_name": "Joueur",
        "lb_score": "Score",
        
        "feedback_title": "Retours & Idées",
        "feedback_desc": "Une idée lumineuse ? Un bug aperçu ? Dites-le nous ci-dessous.",
        
        "lb_tab_standard": "Classique",
        "lb_tab_mult": "Multiplicatif (×)",
        "lb_sort_wins": "Victoires",
        "lb_sort_winrate": "Taux victoire",
        "lb_sort_avg": "Ø Score",
        "lb_sort_hitrate": "Taux réussite",
        "lb_sort_high": "Record",
        "lb_sort_streak": "Série",
        "lb_loading": "Chargement...",
        "lb_global": "GLOBAL RANKINGS",
        "lb_error": "Erreur de chargement.",
        "lb_empty": "Aucune partie dans ce mode.",
        "lb_table_games": "Parties",
        "lb_table_wins": "Victoires",
        "lb_table_quote": "Taux V." ,
        "lb_table_avg": "Ø Score",
        "lb_table_hit": "Précision",
        "lb_table_high": "Record",
        "lb_table_streak": "Série",
        
        "fb_submit": "Envoyer",
        "fb_placeholder": "Votre retour...",

        # Groups leaderboard page
        "lb_group_global_subtitle": "CLASSEMENT DES GROUPES",
        "lb_group_subtitle": "CLASSEMENT DES JOUEURS DU GROUPE",
        "lb_search_placeholder": "Rechercher un groupe par nom…",
        "lb_col_group": "Groupe",
        "lb_players_short": "Joueurs",
        "lb_click_group_hint": "Cliquez sur un groupe pour ouvrir son classement (code à 4 chiffres requis).",
        "lb_no_groups_found": "Aucun groupe trouvé.",
        "lb_hidden_badge": "MASQUÉ",
        "lb_enter_code": "Code du groupe",
        "lb_enter_code_for": "Entrez le code à 4 chiffres de {name}",
        "lb_open_btn": "Ouvrir",
        "lb_code_format_error": "Le code doit contenir 4 chiffres.",
        "lb_code_wrong": "Code incorrect ou inconnu.",
        "lb_back_to_groups": "Retour aux groupes",
        "cancel": "Annuler",
    },
    "hi": {
        # Nav
        "nav_home": "होम (Home)",
        "nav_leaderboard": "लीडरबोर्ड (Leaderboard)",
        "nav_feedback": "प्रतिक्रिया (Feedback)",
        
        # Hero
        "hero_badge": "विज़ार्ड स्कोर ट्रैकर",
        "hero_title_1": "हर चाल।",
        "hero_title_2": "हर जीत।",
        "hero_desc": "अपने विज़ार्ड कार्ड-गेम की रातों का स्कोर स्वचालित रूप से तय करें, और विश्वव्यापी लीडरबोर्ड पर अपने समूह को बढ़ते हुए देखें।",
        "cta_windows": "विंडोज़ के लिए डाउनलोड करें (.exe)",
        "cta_leaderboard": "लीडरबोर्ड देखें →",
        "cta_patreon": "पैट्रियन पर हमें सपोर्ट करें",
        "cta_appstore": "ऐप स्टोर से डाउनलोड करें",
        "cta_playstore": "गूगल प्ले पर उपलब्ध",
        "cta_github": "गिटहब पर कोड देखें",
        "coming_soon": "जल्द आ रहा है",
        
        # Features
        "feat_1_title": "स्वचालित स्कोरिंग",
        "feat_1_desc": "बोलियां और चालें दर्ज करें — ऐप हर राउंड के लिए गणित संभालता है।",
        "feat_2_title": "वैश्विक लीडरबोर्ड",
        "feat_2_desc": "जीत की दर, लकीरें और उच्च स्कोर — देखें कि आपकी टेबल दुनिया भर में कैसी है।",
        "feat_3_title": "निजी समूह",
        "feat_3_desc": "अपने समूह के साथ 4-अंकीय कोड साझा करें और अपने नियमित गेम नाइट्स के लिए एक निजी लीडरबोर्ड रखें।",
        
        # Footer
        "footer_text": "विज़ार्ड स्कोर ट्रैकर",
        
        "leaderboard_title": "ग्लोबल लीडरबोर्ड",
        "leaderboard_desc": "दुनिया भर के सर्वश्रेष्ठ विजार्ड खिलाड़ियों को देखें।",
        "lb_name": "खिलाड़ी",
        "lb_score": "अंक",
        
        "feedback_title": "फ़ीडबैक और विचार",
        "feedback_desc": "कोई बढ़िया विचार है? कोई बग मिला? हमें नीचे बताएं।",
        
        "lb_tab_standard": "स्टैंडर्ड",
        "lb_tab_mult": "गुणात्मक (×)",
        "lb_sort_wins": "जीत",
        "lb_sort_winrate": "जीतने की दर",
        "lb_sort_avg": "Ø स्कोर",
        "lb_sort_hitrate": "हिट दर",
        "lb_sort_high": "उच्च स्कोर",
        "lb_sort_streak": "जीत की लकीर",
        "lb_loading": "डेटा लोड हो रहा है...",
        "lb_global": "GLOBAL RANKINGS",
        "lb_error": "डेटा लोड करने में त्रुटि।",
        "lb_empty": "इस मोड में अभी तक कोई गेम नहीं।",
        "lb_table_games": "गेम",
        "lb_table_wins": "जीत",
        "lb_table_quote": "दर",
        "lb_table_avg": "Ø स्कोर",
        "lb_table_hit": "हिट",
        "lb_table_high": "उच्च स्कोर",
        "lb_table_streak": "लकीर",
        
        "fb_submit": "सबमिट करें",
        "fb_placeholder": "अपना फीडबैक लिखें...",

        # Groups leaderboard page
        "lb_group_global_subtitle": "समूह रैंकिंग",
        "lb_group_subtitle": "समूह के खिलाड़ियों की रैंकिंग",
        "lb_search_placeholder": "नाम से समूह खोजें…",
        "lb_col_group": "समूह",
        "lb_players_short": "खिलाड़ी",
        "lb_click_group_hint": "खिलाड़ियों की रैंकिंग खोलने के लिए किसी समूह पर क्लिक करें (4-अंकीय कोड आवश्यक)।",
        "lb_no_groups_found": "कोई समूह नहीं मिला।",
        "lb_hidden_badge": "छिपा हुआ",
        "lb_enter_code": "समूह कोड दर्ज करें",
        "lb_enter_code_for": "{name} के लिए 4-अंकीय कोड दर्ज करें",
        "lb_open_btn": "खोलें",
        "lb_code_format_error": "कोड 4 अंकों का होना चाहिए।",
        "lb_code_wrong": "गलत या अज्ञात कोड।",
        "lb_back_to_groups": "समूहों पर वापस जाएं",
        "cancel": "रद्द करें",
    }
}
