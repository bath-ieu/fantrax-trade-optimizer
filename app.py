import streamlit as st
import requests
import pandas as pd

# Configuration de la page Streamlit
st.set_page_config(page_title="Fantrax Trade Optimizer", page_icon="🏒", layout="wide")

# --- STYLE CSS PERSONNALISÉ (THEME FANTRAX DARK MODE) ---
st.markdown("""
    <style>
    /* Fond général de l'application */
    .stApp {
        background-color: #0e1621;
        color: #ffffff;
    }
    
    /* Style des onglets */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #17212b;
        padding: 10px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #242f3d;
        color: #ffffff;
        border-radius: 6px;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2b5278 !important;
        font-weight: bold;
    }
    
    /* Cartes et conteneurs */
    div[data-testid="stMetric"] {
        background-color: #17212b;
        border: 1px solid #242f3d;
        padding: 15px;
        border-radius: 10px;
    }
    
    /* Boutons */
    .stButton>button {
        background-color: #2b5278;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #3b6c9b;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏒 Fantrax Trade & Mock Simulator")

# ID de ligue par défaut
DEFAULT_LEAGUE_ID = "35oi8ycimudcfy7x"

# --- BARRE LATÉRALE : CONFIGURATION ---
st.sidebar.header("⚙️ Configuration")
league_id = st.sidebar.text_input("League ID Fantrax", value=DEFAULT_LEAGUE_ID)

@st.cache_data(ttl=300)
def fetch_league_data(l_id):
    """Récupère les informations de la ligue, les rosters et les statistiques depuis l'API de Fantrax."""
    info_url = f"https://www.fantrax.com/fxea/general/getLeagueInfo?leagueId={l_id}"
    rosters_url = f"https://www.fantrax.com/fxea/general/getTeamRosters?leagueId={l_id}"
    
    try:
        info_res = requests.get(info_url)
        rosters_res = requests.get(rosters_url)
        
        info_data = info_res.json() if info_res.status_code == 200 else {}
        rosters_data = rosters_res.json() if rosters_res.status_code == 200 else {}
        
        return info_data, rosters_data
    except Exception as e:
        st.error(f"Erreur de connexion à l'API Fantrax : {e}")
    return {}, {}

def calculate_fantasy_points(player_stats):
    """Calcule les points selon ton barème exact Fantrax."""
    fpts_direct = player_stats.get("fpts", player_stats.get("fantasyPoints", None))
    if fpts_direct is not None and float(fpts_direct) > 0:
        return float(fpts_direct)
        
    goals = float(player_stats.get("g", player_stats.get("goals", 0)))
    assists = float(player_stats.get("a", player_stats.get("assists", 0)))
    blocks = float(player_stats.get("blk", player_stats.get("blocks", 0)))
    hat_tricks = float(player_stats.get("hat", 0))
    
    wins = float(player_stats.get("w", 0))
    shutouts = float(player_stats.get("so", 0))
    otl = float(player_stats.get("otl", 0))
    goal_goals = float(player_stats.get("goalGoals", 0))
    goal_assists = float(player_stats.get("goalAssists", 0))

    points = (
        (goals * 1.0) +
        (assists * 1.0) +
        (blocks * 0.2) +
        (hat_tricks * 2.0) +
        (wins * 2.0) +
        (shutouts * 1.0) +
        (otl * 1.0) +
        (goal_goals * 10.0) +
        (goal_assists * 2.0)
    )
    
    if points == 0:
        pos = player_stats.get("position", player_stats.get("pos", "F"))
        if "G" in pos:
            return 3.5
        elif "D" in pos:
            return 2.0
        else:
            return 2.5
            
    return points

def build_player_maps(league_info, league_rosters):
    """Extrait proprement le dictionnaire des joueurs depuis les réponses de l'API."""
    players_map = {}
    
    for source in [league_info, league_rosters]:
        if not source:
            continue
        p_map = source.get("playerMap", source.get("scorerInfo", source.get("players", {})))
        if isinstance(p_map, dict):
            for p_id, p_info in p_map.items():
                if isinstance(p_info, dict):
                    name = p_info.get("name", p_info.get("fullName", p_id))
                    pos = p_info.get("position", p_info.get("pos", "F"))
                    fpts = calculate_fantasy_points(p_info)
                    players_map[p_id] = {"name": name, "position": pos, "fpts": fpts}

    rosters = league_rosters.get("rosters", {})
    for t_id, t_data in rosters.items():
        items = t_data.get("rosterItems", [])
        for item in items:
            p_id = item.get("id", item.get("playerId"))
            name = item.get("name", item.get("fullName", ""))
            pos = item.get("position", item.get("pos", "F"))
            fpts = calculate_fantasy_points(item)
            
            if p_id:
                if p_id not in players_map or not players_map[p_id]["name"] or players_map[p_id]["name"] == p_id:
                    players_map[p_id] = {
                        "name": name if name else f"Joueur {p_id}",
                        "position": pos,
                        "fpts": fpts if fpts > 0 else 2.5
                    }
                    
    return players_map

if league_id:
    league_info, league_rosters = fetch_league_data(league_id)
    
    if league_info or league_rosters:
        league_name = league_info.get("leagueInfo", {}).get("name", "Ma Ligue Fantrax")
        st.subheader(f"📊 Ligue : **{league_name}**")
        
        teams_data = league_info.get("teamInfo", {})
        team_options = {t_id: t_info.get("name", f"Équipe {t_id}") for t_id, t_info in teams_data.items()}
        roster_dict = league_rosters.get("rosters", {})
        global_players_map = build_player_maps(league_info, league_rosters)

        tab1, tab2 = st.tabs(["🔄 Simulateur de Trade", "🤖 Suggestions Automatiques"])

        # ==========================================
        # ONGLET 1 : SIMULATEUR DE TRADE
        # ==========================================
        with tab1:
            st.header("🔄 Simuler un Échange")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("👤 Ton Équipe")
                my_team_id = st.selectbox(
                    "Sélectionne ton équipe", 
                    options=list(team_options.keys()), 
                    format_func=lambda x: team_options[x], 
                    key="my_team_tab1"
                )
                
            with col2:
                st.subheader("👥 Équipe Adverse")
                other_team_options = [t for t in team_options.keys() if t != my_team_id]
                other_team_id = st.selectbox(
                    "Sélectionne l'autre équipe", 
                    options=other_team_options, 
                    format_func=lambda x: team_options[x], 
                    key="other_team_tab1"
                )
                
            my_roster_items = roster_dict.get(my_team_id, {}).get("rosterItems", [])
            other_roster_items = roster_dict.get(other_team_id, {}).get("rosterItems", [])
            
            my_players_dict = {}
            for item in my_roster_items:
                p_id = item.get("id", item.get("playerId"))
                p_info = global_players_map.get(p_id, {"name": item.get("name", p_id), "position": item.get("position", "F"), "fpts": 2.5})
                my_players_dict[p_info["name"]] = p_info

            other_players_dict = {}
            for item in other_roster_items:
                p_id = item.get("id", item.get("playerId"))
                p_info = global_players_map.get(p_id, {"name": item.get("name", p_id), "position": item.get("position", "F"), "fpts": 2.5})
                other_players_dict[p_info["name"]] = p_info
            
            st.markdown("### ⚖️ Choix des Joueurs à Échanger")
            col_trade_1, col_trade_2 = st.columns(2)
            
            with col_trade_1:
                giving_player_names = st.multiselect(
                    "Joueurs que TU donnes :", 
                    options=list(my_players_dict.keys()),
                    key="giving_tab1"
                )
                
            with col_trade_2:
                receiving_player_names = st.multiselect(
                    "Joueurs que TU reçois :", 
                    options=list(other_players_dict.keys()),
                    key="receiving_tab1"
                )
                
            if giving_player_names or receiving_player_names:
                st.markdown("---")
                st.header("📈 Analyse & Évaluation de l'Échange")
                
                pts_given = sum([my_players_dict[name]["fpts"] for name in giving_player_names])
                pts_received = sum([other_players_dict[name]["fpts"] for name in receiving_player_names])
                diff = pts_received - pts_given
                
                res_col1, res_col2, res_col3 = st.columns(3)
                with res_col1:
                    st.metric(label="Points que tu donnes", value=f"{pts_given:.2f} pts")
                with res_col2:
                    st.metric(label="Points que tu reçois", value=f"{pts_received:.2f} pts")
                with res_col3:
                    st.metric(label="Différence nette", value=f"{diff:+.2f} pts", delta=f"{diff:+.2f} pts")
                    
                if diff > 0:
                    st.success(f"✅ **EXCELLENT TRADE !** Tu gagnes environ **{abs(diff):.2f} points**.")
                elif diff < 0:
                    st.error(f"⚠️ **MAUVAIS TRADE !** Tu perds environ **{abs(diff):.2f} points**.")
                else:
                    st.info("⚖️ **TRADE ÉQUILIBRÉ !**")
                    
                details = []
                for name in giving_player_names:
                    p = my_players_dict[name]
                    details.append({"Action": "Tu Donnes", "Joueur": name, "Position": p.get("position", "N/A"), "Points Projetés": round(p.get("fpts", 0), 2)})
                for name in receiving_player_names:
                    p = other_players_dict[name]
                    details.append({"Action": "Tu Reçois", "Joueur": name, "Position": p.get("position", "N/A"), "Points Projetés": round(p.get("fpts", 0), 2)})
                    
                if details:
                    st.dataframe(pd.DataFrame(details), use_container_width=True)

        # ==========================================
        # ONGLET 2 : SUGGESTIONS AUTOMATIQUES
        # ==========================================
        with tab2:
            st.header("🤖 Recommandations d'Échanges 1 pour 1")
            
            my_team_id_auto = st.selectbox(
                "Choisis ton équipe pour générer les suggestions :", 
                options=list(team_options.keys()), 
                format_func=lambda x: team_options[x], 
                key="my_team_tab2"
            )
            
            min_gain = st.slider("Gain minimal recherché (Points) :", min_value=0.1, max_value=5.0, value=0.5, step=0.1)
            
            if st.button("🔍 Générer les suggestions d'échanges"):
                my_roster_items = roster_dict.get(my_team_id_auto, {}).get("rosterItems", [])
                my_players_dict = {}
                for item in my_roster_items:
                    p_id = item.get("id", item.get("playerId"))
                    p_info = global_players_map.get(p_id, {"name": item.get("name", p_id), "position": item.get("position", "F"), "fpts": 2.5})
                    my_players_dict[p_info["name"]] = p_info
                
                suggestions = []
                
                for other_t_id, other_t_info in teams_data.items():
                    if other_t_id == my_team_id_auto:
                        continue
                    
                    other_team_name = other_t_info.get("name", f"Équipe {other_t_id}")
                    other_roster_items = roster_dict.get(other_t_id, {}).get("rosterItems", [])
                    other_players_dict = {}
                    for item in other_roster_items:
                        p_id = item.get("id", item.get("playerId"))
                        p_info = global_players_map.get(p_id, {"name": item.get("name", p_id), "position": item.get("position", "F"), "fpts": 2.5})
                        other_players_dict[p_info["name"]] = p_info
                    
                    for my_p_name, my_p_obj in my_players_dict.items():
                        my_p_val = my_p_obj["fpts"]
                        
                        for oth_p_name, oth_p_obj in other_players_dict.items():
                            oth_p_val = oth_p_obj["fpts"]
                            gain = oth_p_val - my_p_val
                            
                            if gain >= min_gain:
                                suggestions.append({
                                    "Équipe Adverse": other_team_name,
                                    "Tu Donnes": my_p_name,
                                    "Pts Ton Joueur": round(my_p_val, 2),
                                    "Tu Reçois": oth_p_name,
                                    "Pts Joueur Reçu": round(oth_p_val, 2),
                                    "Gain Net (Pts)": round(gain, 2)
                                })
                
                if suggestions:
                    df_sug = pd.DataFrame(suggestions).sort_values(by="Gain Net (Pts)", ascending=False)
                    st.success(f"🎉 **{len(suggestions)} opportunités de trades trouvées !**")
                    st.dataframe(df_sug, use_container_width=True)
                else:
                    st.warning("Aucune suggestion trouvée avec ce niveau de gain minimal.")

    else:
        st.error("Impossible de charger les données Fantrax. Vérifie l'accès à la ligue.")
