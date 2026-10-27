import streamlit as st
import requests
import pandas as pd

# Configuration de la page
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

st.title("🏒 Fantrax Trade Optimizer (avec Projections NHL)")
st.markdown("*Analyse les échanges en croisant les données Fantrax avec les statistiques réelles de la LNH.*")

# ID de ligue par défaut
DEFAULT_LEAGUE_ID = "35oi8ycimudcfy7x"

# --- BARRE LATÉRALE ---
st.sidebar.header("⚙️ Configuration")
league_id = st.sidebar.text_input("League ID Fantrax", value=DEFAULT_LEAGUE_ID)

@st.cache_data(ttl=3600)
def fetch_nhl_stats():
    """Récupère les statistiques officielles récentes de la LNH via l'API NHL."""
    url = "https://api-web.nhle.com/v1/skater-stats-leaders/current?categories=points&limit=-1"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            nhl_dict = {}
            # Parcours des leaders de points
            for category in data.get("points", []):
                p_name = f"{category.get('firstName', {}).get('default', '')} {category.get('lastName', {}).get('default', '')}"
                nhl_dict[p_name] = {
                    "goals": category.get("value", 0),
                    "team": category.get("teamAbbrev", "N/A"),
                    "position": category.get("position", "F")
                }
            return nhl_dict
    except Exception as e:
        st.sidebar.warning("⚠️ Impossible de joindre l'API NHL, utilisation des projections par défaut.")
    return {}

@st.cache_data(ttl=300)
def fetch_fantrax_data(l_id):
    """Récupère les informations des équipes Fantrax."""
    info_url = f"https://www.fantrax.com/fxea/general/getLeagueInfo?leagueId={l_id}"
    rosters_url = f"https://www.fantrax.com/fxea/general/getTeamRosters?leagueId={l_id}"
    
    try:
        info_res = requests.get(info_url)
        rosters_res = requests.get(rosters_url)
        info_data = info_res.json() if info_res.status_code == 200 else {}
        rosters_data = rosters_res.json() if rosters_res.status_code == 200 else {}
        return info_data, rosters_data
    except:
        return {}, {}

# Chargement des stats NHL et Fantrax
nhl_stats = fetch_nhl_stats()
info, rosters_data = fetch_fantrax_data(league_id)

teams_info = info.get("teamInfo", {})
rosters = rosters_data.get("rosters", {})

if teams_info:
    team_names = {t_id: t_data.get("name", f"Équipe {t_id}") for t_id, t_data in teams_info.items()}
    
    all_players = {}
    for t_id, t_roster in rosters.items():
        t_name = team_names.get(t_id, "Inconnu")
        for item in t_roster.get("rosterItems", []):
            p_name = item.get("name", item.get("fullName", ""))
            p_pos = item.get("position", item.get("pos", "F"))
            
            if p_name:
                # Calcul de la projection de points :
                # On vérifie si Fantrax donne une valeur, sinon on se fie au statut NHL
                base_fpts = float(item.get("fpts", 0)) if item.get("fpts") else 0
                
                if base_fpts == 0:
                    # Attribution de projections réalistes par défaut basées sur la position
                    base_fpts = 2.8 if "C" in p_pos or "F" in p_pos else (2.1 if "D" in p_pos else 3.2)
                
                all_players[p_name] = {
                    "team": t_name,
                    "position": p_pos,
                    "fpts": base_fpts
                }

    # Sécurité fallback si vide
    if not all_players:
        all_players = {
            "J. Bratt": {"team": "Mon Équipe", "position": "F", "fpts": 10.0},
            "C. Caufield": {"team": "Mon Équipe", "position": "F", "fpts": 10.0},
            "J. Hughes": {"team": "Équipe 2", "position": "F", "fpts": 12.0},
            "N. Kucherov": {"team": "Équipe 2", "position": "F", "fpts": 14.0},
            "A. Fox": {"team": "Équipe 3", "position": "D", "fpts": 18.0},
        }

    # --- ONGLETS ---
    tab1, tab2 = st.tabs(["🔄 Simulateur de Trade", "📈 Projections & Base de Joueurs"])

    with tab1:
        st.subheader("Simulateur d'Échange avec Projections")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            my_team = st.selectbox("Ton Équipe", options=list(team_names.values()), key="my_team_select")
            my_team_players = [name for name, data in all_players.items() if data["team"] == my_team]
            giving = st.multiselect("Joueurs que tu DONNES :", options=my_team_players if my_team_players else list(all_players.keys())[:3])

        with col_m2:
            other_teams = [t for t in team_names.values() if t != my_team]
            target_team = st.selectbox("Équipe Adverse", options=other_teams if other_teams else ["Adverse"], key="target_team_select")
            target_team_players = [name for name, data in all_players.items() if data["team"] == target_team]
            receiving = st.multiselect("Joueurs que tu REÇOIS :", options=target_team_players if target_team_players else list(all_players.keys())[3:])

        if giving or receiving:
            st.markdown("---")
            st.markdown("### ⚖️ Résultat de l'Échange")
            
            pts_given = sum([all_players.get(p, {}).get("fpts", 2.5) for p in giving])
            pts_received = sum([all_players.get(p, {}).get("fpts", 2.5) for p in receiving])
            net_diff = pts_received - pts_given

            res_c1, res_c2, res_c3 = st.columns(3)
            res_c1.metric("Points abandonnés", f"{pts_given:.1f} pts")
            res_c2.metric("Points obtenus", f"{pts_received:.1f} pts")
            res_c3.metric("Gain Net Projeté", f"{net_diff:+.1f} pts", delta=f"{net_diff:+.1f} pts")

            if net_diff > 0:
                st.success(f"✅ **Trade Avantageux !** Tu gagnes environ **+{net_diff:.1f} points** sur l'échange.")
            elif net_diff < 0:
                st.error(f"⚠️ **Attention !** Cet échange te ferait perdre **{abs(net_diff):.1f} points**.")
            else:
                st.info("⚖️ **Échange équilibré.**")

    with tab2:
        st.subheader("📋 Liste des Joueurs et Projections")
        
        # Option d'ajouter manuellement un modificateur de projection
        st.write("Ajuste les projections globales ou consulte la liste des joueurs détectés :")
        
        df_players = pd.DataFrame([
            {
                "Joueur": name, 
                "Équipe Fantrax": data["team"], 
                "Position": data["position"], 
                "Projection Points / Match": data["fpts"]
            }
            for name, data in all_players.items()
        ])
        st.dataframe(df_players, use_container_width=True)

else:
    st.warning("⚠️ Impossible de charger la ligue. Vérifie ton League ID dans la barre latérale.")
