import streamlit as st
import requests
import pandas as pd

# Configuration de la page Streamlit
st.set_page_config(page_title="Fantrax Trade Optimizer", page_icon="🏒", layout="wide")

# --- DESIGN DARK MODE FANTRAX ---
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1621;
        color: #ffffff;
    }
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
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2b5278 !important;
    }
    div[data-testid="stMetric"] {
        background-color: #17212b;
        border: 1px solid #242f3d;
        padding: 15px;
        border-radius: 10px;
    }
    .stButton>button {
        background-color: #2b5278;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #3b6c9b;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏒 Fantrax Trade Optimizer")
st.markdown("*Analyse et simulation d'échanges basées sur les données réelles de votre ligue.*")

DEFAULT_LEAGUE_ID = "35oi8ycimudcfy7x"

# --- BARRE LATÉRALE ---
st.sidebar.header("⚙️ Configuration")
league_id = st.sidebar.text_input("League ID Fantrax", value=DEFAULT_LEAGUE_ID)

@st.cache_data(ttl=600)
def load_league_from_fantrax(l_id):
    """
    Récupère les informations des équipes et résout la correspondance 
    des joueurs via l'API Fantrax et l'API NHL.
    """
    info_url = f"https://www.fantrax.com/fxea/general/getLeagueInfo?leagueId={l_id}"
    rosters_url = f"https://www.fantrax.com/fxea/general/getTeamRosters?leagueId={l_id}"
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        res_info = requests.get(info_url, headers=headers).json()
        res_rosters = requests.get(rosters_url, headers=headers).json()
    except Exception as e:
        return {}, {}
    
    # 1. Cartographie des équipes
    teams_raw = res_info.get("teamInfo", {})
    teams_map = {t_id: t_data.get("name", f"Équipe {t_id}") for t_id, t_data in teams_raw.items()}
    
    # 2. Cartographie globale des joueurs (résolution des IDs)
    player_lookup = {}
    
    # Extraire depuis 'playerMap' ou 'scorerInfo' si présent dans la réponse
    for source in [res_info, res_rosters]:
        p_source = source.get("playerMap", source.get("scorerInfo", {}))
        if isinstance(p_source, dict):
            for pid, pdata in p_source.items():
                if isinstance(pdata, dict):
                    p_name = pdata.get("name", pdata.get("fullName"))
                    p_pos = pdata.get("position", pdata.get("pos", "F"))
                    if p_name:
                        player_lookup[pid] = {"name": p_name, "pos": p_pos}

    # 3. Traitement des rosters par équipe
    rosters = res_rosters.get("rosters", {})
    parsed_players = {}
    
    for t_id, r_data in rosters.items():
        team_name = teams_map.get(t_id, f"Équipe {t_id}")
        items = r_data.get("rosterItems", [])
        
        for item in items:
            pid = item.get("id", item.get("playerId"))
            
            # Résolution du nom : direct -> table globale -> fallback
            if pid in player_lookup:
                p_name = player_lookup[pid]["name"]
                p_pos = player_lookup[pid]["pos"]
            else:
                p_name = item.get("name", item.get("fullName", f"Joueur ({pid})"))
                p_pos = item.get("position", item.get("pos", "F"))
            
            # Points Fantrax
            fpts = item.get("fpts", item.get("fantasyPoints", 0))
            try:
                fpts = float(fpts)
            except:
                fpts = 0.0
                
            parsed_players[p_name] = {
                "team": team_name,
                "position": p_pos,
                "fpts": fpts,
                "id": pid
            }
            
    return teams_map, parsed_players

# Chargement des données
teams_map, players_data = load_league_from_fantrax(league_id)

if players_data:
    all_teams = sorted(list(set(d["team"] for d in players_data.values())))
    
    tab1, tab2 = st.tabs(["🔄 Simulateur de Trade", "📋 Effectifs & Points"])

    with tab1:
        st.subheader("Simulateur d'Échange (Mock Trade)")
        
        col1, col2 = st.columns(2)
        with col1:
            my_team = st.selectbox("Sélectionne ton équipe :", options=all_teams, key="my_team")
            my_players = [p for p, d in players_data.items() if d["team"] == my_team]
            giving = st.multiselect("Joueurs que TU DONNES :", options=sorted(my_players))
            
        with col2:
            other_teams = [t for t in all_teams if t != my_team]
            target_team = st.selectbox("Sélectionne l'équipe adverse :", options=other_teams if other_teams else all_teams, key="target_team")
            target_players = [p for p, d in players_data.items() if d["team"] == target_team]
            receiving = st.multiselect("Joueurs que TU REÇOIS :", options=sorted(target_players))

        if giving or receiving:
            st.markdown("---")
            st.markdown("### ⚖️ Résultat de l'Échange")
            
            pts_given = sum([players_data[p]["fpts"] for p in giving])
            pts_received = sum([players_data[p]["fpts"] for p in receiving])
            diff = pts_received - pts_given

            c1, c2, c3 = st.columns(3)
            c1.metric("Points donnés", f"{pts_given:.2f} pts")
            c2.metric("Points reçus", f"{pts_received:.2f} pts")
            c3.metric("Différence nette", f"{diff:+.2f} pts", delta=f"{diff:+.2f} pts")

            if diff > 0:
                st.success(f"✅ **EXCELLENT TRADE !** Gain net de **+{diff:.2f} points**.")
            elif diff < 0:
                st.error(f"⚠️ **DÉSAVANTAGEUX !** Perte nette de **{abs(diff):.2f} points**.")
            else:
                st.info("⚖️ **ÉCHANGE ÉQUILIBRÉ.**")

    with tab2:
        st.subheader("📋 Base de données des joueurs de la ligue")
        df_display = pd.DataFrame([
            {"Joueur": p, "Équipe": d["team"], "Position": d["position"], "Points Fantrax": d["fpts"]}
            for p, d in players_data.items()
        ])
        st.dataframe(df_display, use_container_width=True)

else:
    st.warning("⚠️ Chargement des données de la ligue en cours ou ID invalide.")
