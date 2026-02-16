#!/usr/bin/env python3
import os, sys, pandas as pd, numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch, FontManager

# HPFA Standart Ayarları
PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0

def load_hpfa_data(path):
    # CSV yükleme (Semicolon delimiter desteği ile)
    df = pd.read_csv(path, sep=';')
    df = df.dropna(subset=['pos_x', 'pos_y', 'team'])
    
    # Oyuncu ismini koddan ayıklama
    def clean_player(code):
        if pd.isna(code): return "Unknown"
        parts = str(code).split(' - ')
        name_part = parts[0]
        if '. ' in name_part:
            return name_part.split('. ', 1)[1].strip()
        return name_part.strip()

    df['player'] = df['code'].apply(clean_player)
    return df

def process_network(df, team_name):
    team_df = df[df['team'].str.contains(team_name, na=False)].copy()
    
    # Koordinat Normalizasyonu (105x68 ölçeğine)
    # 2. yarıda saha değişimi simetrisi (HP-Flip)
    team_df.loc[team_df['half'] == 2, 'pos_x'] = 100 - team_df['pos_x']
    team_df.loc[team_df['half'] == 2, 'pos_y'] = 100 - team_df['pos_y']

    # Başarılı Pasları Filtrele
    passes = team_df[team_df['action'] == "Paslar adresi bulanlar"].copy()
    
    # Ortalama Pozisyonlar (Mikro Katman)
    avg_pos = team_df.groupby('player').agg({'pos_x': 'mean', 'pos_y': 'mean', 'ID': 'count'}).reset_index()
    avg_pos.columns = ['player', 'x', 'y', 'count']

    # Pas Bağlantıları (Mezzo Katman)
    # Bir sonraki aksiyonun aynı takımdan ve pas olup olmadığını kontrol et
    passes['next_player'] = passes['player'].shift(-1)
    passes['next_team'] = passes['team'].shift(-1)
    
    # Aynı takım içi ve makul zaman aralığındaki paslar
    edges = passes[passes['team'] == passes['next_team']].groupby(['player', 'next_player']).size().reset_index(name='pass_count')
    
    return avg_pos, edges

def plot_hpfa_v3(avg_pos, edges, team_name, out_path):
    pitch = Pitch(pitch_type='custom', pitch_length=105, pitch_width=68, 
                  line_color='#c5daf9', pitch_color='#0f141a')
    fig, ax = pitch.draw(figsize=(16, 11))
    
    # 1. Katman: Pas Ağları (Edge Dynamics)
    # Sadece 2 ve üzeri paslaşmaları çiz (Gürültü Filtresi)
    mask = edges['pass_count'] > 2
    max_width = 15
    for _, row in edges[mask].iterrows():
        p1 = avg_pos[avg_pos['player'] == row['player']]
        p2 = avg_pos[avg_pos['player'] == row['next_player']]
        
        if not p1.empty and not p2.empty:
            width = (row['pass_count'] / edges['pass_count'].max()) * max_width
            # Vektörel İlerleme Rengi (Kırmızı = Dikey/Agresif, Mavi = Yatay)
            dx = abs(p2.x.values[0] - p1.x.values[0])
            color = '#e74c3c' if dx > 15 else '#3498db'
            
            pitch.lines(p1.x, p1.y, p2.x, p2.y, lw=width, color=color, alpha=0.5, ax=ax)

    # 2. Katman: Oyuncu Düğümleri (Centrality)
    nodes = pitch.scatter(avg_pos.x, avg_pos.y, s=avg_pos['count'] * 10,
                         c='#f1c40f', edgecolors='#ffffff', linewidth=2, alpha=1, ax=ax)

    # 3. Katman: Ontolojik Etiketleme
    for _, row in avg_pos.iterrows():
        pitch.annotate(row.player, xy=(row.x, row.y), c='white', va='center',
                       ha='center', size=10, weight='bold', ax=ax,
                       bbox=dict(facecolor='#0f141a', alpha=0.6, edgecolor='none', boxstyle='round,pad=0.2'))

    plt.title(f"HPFA SYSTEM - TACTICAL FLOW ANALYSIS: {team_name}", color='white', size=24, pad=20)
    plt.savefig(out_path, facecolor='#0f141a', dpi=300, bbox_inches='tight')
    plt.close()

def main():
    if len(sys.argv) < 2:
        print("Kullanım: python hpfa_core_engine_v3.py <csv_dosya_yolu>")
        sys.exit(1)

    csv_path = sys.argv[1]
    df = load_hpfa_data(csv_path)
    
    teams = df['team'].unique()
    for team in teams:
        if pd.isna(team): continue
        avg_pos, edges = process_network(df, team)
        clean_name = team.split(' (')[0].replace(' ', '_')
        out_name = f"HPFA_PassNet_{clean_name}.png"
        plot_hpfa_v3(avg_pos, edges, team, out_name)
        print(f"Analiz Tamamlandı: {out_name}")

if __name__ == "__main__":
    main()
