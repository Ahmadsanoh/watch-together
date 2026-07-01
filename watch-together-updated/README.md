# Watch Together — Pôle 1 (Sujet B)

Salon virtuel synchronisé : le présentateur pilote ce que voient tous les invités en temps réel, et peut présenter plusieurs types de contenu, pas seulement une vidéo HLS.

## Fonctionnalités

### Présentation (présentateur uniquement)
- **Flux HLS de démo** (par défaut)
- **Upload de fichier** (vidéo ou image) — diffusé à tous les invités via une URL servie par le serveur
- **Vidéo YouTube** — collez un lien, synchronisé via l'API YouTube (play/pause automatiques, boutons -10s/+10s pour le seek)
- **Image** — via upload ou URL directe
- **Partage d'écran + micro** en direct via WebRTC — les invités voient l'écran du présentateur et l'entendent en temps réel

### Pour tous les participants
- Salon synchronisé avec code de room et lien partageable (`?room=xxx`)
- Liste des participants en temps réel avec leur nom et leur rôle
- Chat textuel en direct
- Réactions emoji flottantes (👍 ❤️ 😂 👏 🎉 😮)
- Reconnexion automatique en cas de coupure réseau, avec resynchronisation
- Gestion du départ du présentateur ("Prendre la main") et transfert de contrôle explicite

## Structure

```
watch-together/
  server/   -> serveur Node (Express + WebSocket), upload de fichiers, relais WebRTC
  client/   -> application React (Stage.jsx pour l'affichage, Room.jsx pour l'orchestration)
```

## Démarrage rapide

### 1. Serveur

```bash
cd server
npm install
npm run dev
```

Le serveur tourne sur `http://localhost:4000` (WebSocket + upload de fichiers servis depuis `/uploads`).

### 2. Client

```bash
cd client
npm install
npm run dev
```

Ouvrez `http://localhost:5173`. Pour des tests fiables à plusieurs onglets, préférez `npm run build` puis `npm run preview`.

## Scénarios de test

### Partage d'écran + micro
1. Le présentateur clique "🖥️ Partager mon écran + micro", choisit l'écran/fenêtre à partager, autorise le micro si demandé.
2. Les invités doivent voir l'écran du présentateur en direct, avec le son.
3. Le présentateur clique "⏹ Arrêter le partage" (ou ferme le partage depuis le bandeau natif du navigateur) : tout le monde repasse automatiquement au flux HLS par défaut.

### Upload de fichier
1. Le présentateur clique "Uploader vidéo / image" et sélectionne un fichier local.
2. Une fois l'envoi terminé, tous les invités voient le nouveau contenu, avec synchronisation play/pause/seek si c'est une vidéo.

### YouTube
1. Le présentateur colle un lien YouTube et clique "Partager la vidéo".
2. Les invités voient la même vidéo. Le présentateur peut utiliser play/pause natif et les boutons -10s/+10s pour ajuster la position chez tout le monde.

### Image
1. Le présentateur colle une URL d'image ou en upload une, clique "Partager l'image".
2. Tous les invités voient l'image affichée en plein cadre.

### Chat et participants
1. N'importe quel participant peut écrire dans le chat ; tout le monde le voit en direct.
2. Le présentateur peut cliquer "Transférer" à côté d'un invité dans la liste des participants pour lui donner le contrôle directement.

## Limites connues (à garder en tête pour la démo)

- Le partage d'écran utilise une architecture WebRTC en étoile (le présentateur ouvre une connexion directe vers chaque invité). Convient bien à un petit groupe (jusqu'à 5-10 invités) comme dans un contexte de démo ou de petite équipe ; au-delà, il faudrait un SFU (serveur de médias) pour plus de robustesse.
- Aucun serveur TURN n'est configuré (seulement un STUN public Google). Sur certains réseaux d'entreprise très restrictifs, la connexion WebRTC peut échouer ; testez en amont sur le réseau utilisé pour la soutenance.
- Les fichiers uploadés sont stockés localement sur le serveur (dossier `server/uploads`), sans limite de durée de vie ni nettoyage automatique pour l'instant.

## Points à adapter par l'équipe

- **Flux sécurisé du Pôle 2** : remplacer le flux HLS de démo par le flux chiffré AES-128 + clé éphémère.
- **Authentification** : actuellement un simple nom + code de room. À aligner avec le mécanisme du Pôle 2 pour l'intégration notée (bloc B, 10 pts).
- **Métadonnées IA du Pôle 3** : prévoir un emplacement sous le Stage pour afficher chapitres/résumés.

## Variables d'environnement (client)

```
VITE_WS_URL=ws://votre-serveur:4000
```
