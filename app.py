import streamlit as st
import requests
import pandas as pd

# Configuration de la page Streamlit
st.set_page_config(page_title="Fantrax Trade Optimizer", page_icon="🏒", layout="wide")

st.title("🏒 Fantrax Trade & Mock Simulator")

# ID de ligue par défaut
DEFAULT_LEAGUE_ID = "35oi8ycimudcfy7x"

# --- BARRE LATÉRALE : CONFIGURATION ---
st.sidebar.header("⚙️ Configuration")
league_id = st.sidebar.text_input("League ID Fantrax", value=DEFAULT_LEAGUE_ID)

# --- BASE DE DONNÉES DE PROJECTIONS (EXEMPLES / PAR DÉFAUT) ---
# Dans une étape ultérieure, ces projections pourront être chargées depuis un fichier CSV ou web-scrapées.
DEFAULT_PROJECTIONS = {
    "Center": 2.8,       # Moyenne de points/match pour un C standard
    "Winger": 2.5,       # Moyenne de points/match pour un Ailier standard
    "Defenseman": 2.0,   # Moyenne de points/match pour un D standard
    "Goaltender": 3.5,   # Moyenne de points/match pour un Gardien standard
}

@st.cache_data(ttl=300)
def fetch_league_data(l_id):
    """Récupère les informations de la ligue et les rosters depuis l'API de Fantrax."""
    info_url = f"https://www.fantrax.com/fxea/general/getLeagueInfo?leagueId={l_id}"
    rosters_url = f"https://www.fantrax.com/fxea/general/getTeamRosters?leagueId={l_id}"
    
    try:
        info_res = requests.get(info_url)
        rosters_res = requests.get(rosters_url)
        
        if info_res.status_code == 200 and rosters_res.status_code == 200:
            return info_res.json(), rosters_res.json()
    except Exception as e:
        st.error(f"Erreur de connexion à l'API Fantrax : {e}")
    return None, None

def get_player_projection(player_info):
    """Extrait ou calcule la valeur projetée d'un joueur en points par match."""
    # Si Fantrax fournit une projection directe ou un nombre de points fantasy
    fpts = player_info.get("fpts", None)
    if fpts is not None and float(fpts) > 0:
        return float(fpts)
    
    # Sinon, attribution d'une valeur basée sur le poste/position
    pos = player_info.get("position", "Winger")
    for key, val in DEFAULT_PROJECTIONS.items():
        if key.lower() in pos.lower():
            return val
    return 2.2  # Valeur par défaut si inconnue

if league_id:
    league_info, league_rosters = fetch_league_data(league_id)
    
    if league_info and league_rosters:
        # Extraire le nom de la ligue
        league_name = league_info.get("leagueInfo", {}).get("name", "Ma Ligue Fantrax")
        st.subheader(f"📊 Ligue : **{league_name}**")
        
        # Structure des équipes
        teams_data = league_info.get("teamInfo", {})
        team_options = {t_id: t_info.get("name", f"Équipe {t_id}") for t_id, t_info in teams_data.items()}
        
        # --- SECTION SIMULATEUR DE TRADE ---
        st.markdown("---")
        st.header("🔄 Simulateur d'Échange (Mock Trade)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("👤 Ton Équipe")
            my_team_id = st.selectbox(
                "Sélectionne ton équipe", 
                options=list(team_options.keys()), 
                format_func=lambda x: team_options[x], 
                key="my_team"
            )
            
        with col2:
            st.subheader("👥 Équipe Adverse")
            other_team_options = [t for t in team_options.keys() if t != my_team_id]
            other_team_id = st.selectbox(
                "Sélectionne l'autre équipe", 
                options=other_team_options, 
                format_func=lambda x: team_options[x], 
                key="other_team"
            )
            
        # Extraire les rosters
        roster_dict = league_rosters.get("rosters", {})
        
        my_roster_items = roster_dict.get(my_team_id, {}).get("rosterItems", [])
        other_roster_items = roster_dict.get(other_team_id, {}).get("rosterItems", [])
        
        # Dictionnaires {Nom du joueur: Objet joueur} pour recherche rapide
        my_players_dict = {p.get("name", p.get("id")): p for p in my_roster_items} if my_roster_items else {}
        other_players_dict = {p.get("name", p.get("id")): p for p in other_roster_items} if other_roster_items else {}
        
        st.markdown("### ⚖️ Choix des Joueurs à Échanger")
        col_trade_1, col_trade_2 = st.columns(2)
        
        with col_trade_1:
            giving_player_names = st.multiselect(
                "Joueurs que TU donnes :", 
                options=list(my_players_dict.keys())
            )
            
        with col_trade_2:
            receiving_player_names = st.multiselect(
                "Joueurs que TU reçois :", 
                options=list(other_players_dict.keys())
            )
            
        # --- CALCUL ET ÉVALUATION DU TRADE ---
        if giving_player_names or receiving_player_names:
            st.markdown("---")
            st.header("📈 Analyse & Évaluation de l'Échange")
            
            # Calcul des points donnes vs reçus
            pts_given = sum([get_player_projection(my_players_dict[name]) for name in giving_player_names])
            pts_received = sum([get_player_projection(other_players_dict[name]) for name in receiving_player_names])
            
            diff = pts_received - pts_given
            
            res_col1, res_col2, res_col3 = st.columns(3)
            
            with res_col1:
                st.metric(label="Points que tu donnes", value=f"{pts_given:.2f} pts")
            with res_col2:
                st.metric(label="Points que tu reçois", value=f"{pts_received:.2f} pts")
            with res_col3:
                st.metric(label="Différence nette (Gain/Perte)", value=f"{diff:+.2f} pts", delta=f"{diff:+.2f} pts")
                
            # Verdict
            if diff > 0:
                st.success(f"✅ **EXCELLENT TRADE !** Tu gagnes environ **{abs(diff):.2f} points** dans cet échange.")
            elif diff < 0:
                st.error(f"⚠️ **MAUVAIS TRADE !** Tu perds environ **{abs(diff):.2f} points** dans cet échange.")
            else:
                st.info("⚖️ **TRADE ÉQUILIBRÉ !** La valeur des joueurs échangés est identique.")
                
            # Détails par joueur
            st.markdown("#### 🔍 Détail par joueur :")
            
            details = []
            for name in giving_player_names:
                p = my_players_dict[name]
                details.append({
                    "Action": "Tu Donnes",
                    "Joueur": name,
                    "Position": p.get("position", "N/A"),
                    "Points Projetés": get_player_projection(p)
                })
            for name in receiving_player_names:
                p = other_players_dict[name]
                details.append({
                    "Action": "Tu Reçois",
                    "Joueur": name,
                    "Position": p.get("position", "N/A"),
                    "Points Projetés": get_player_projection(p)
                })
                
            if details:
                st.dataframe(pd.DataFrame(details), use_container_width=True)

    else:
        st.error("Impossible de charger les données Fantrax. Vérifie que la ligue est accessible.")
