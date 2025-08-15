# Flappy Bird - Mini

**Flappy Bird - Mini** est une version minimaliste du célèbre jeu **Flappy Bird**, codée en **Python** avec **pygame**, contenue dans un seul fichier `.py`.  
L’objectif est simple : contrôler un petit oiseau pour qu’il passe à travers des interstices entre des tuyaux sans les toucher, tout en évitant le sol.  
À chaque passage réussi, vous gagnez un point. La difficulté augmente progressivement : les tuyaux vont plus vite et l’écart se réduit.

---

## 🛠️ Installation

1. **Cloner le dépôt :**
```bash
git clone https://github.com/P1erreD/Flappy-Bird.git
cd Flappy-Bird
````

2. **Installer les dépendances :**

```bash
pip install pygame
```

3. **Lancer le jeu :**

```bash
python flappybird.py
```

---

## 🎯 Règles du jeu

* **But :** Survivez le plus longtemps possible en franchissant des interstices entre des tuyaux.
* **Score :** +1 point chaque fois que l’oiseau passe un ensemble de tuyaux.
* **Difficulté :** Plus le score est élevé, plus le jeu devient difficile.

---

## 🎮 Contrôles

| Action                    | Touche / Souris                  |
| ------------------------- | -------------------------------- |
| Sauter / Battre des ailes | **Espace**, **↑** ou clic gauche |
| Pause / Reprendre         | **P**                            |
| Redémarrer                | **R**                            |
| Quitter                   | **Échap**                        |

---

## 📜 Licence

Ce projet est distribué sous licence **MIT** — voir le fichier [LICENSE](LICENSE) pour plus de détails.
