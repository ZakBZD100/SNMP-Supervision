# Guide de Sécurité - SNMP Supervision

## ⚠️ ATTENTION : Protection des Informations Sensibles

### Problème Identifié
Vos informations sensibles ont été exposées dans le fichier de configuration :
- Email : ziko.elbouzidi@gmail.com
- Mot de passe Gmail : jywciwygnzfdljsn

### Actions Immédiates à Effectuer

1. **Changez immédiatement votre mot de passe Gmail**
   - Allez sur https://myaccount.google.com/security
   - Changez votre mot de passe principal
   - Révoquez tous les mots de passe d'application

2. **Créez un nouveau mot de passe d'application**
   - Dans les paramètres de sécurité Google
   - Générez un nouveau mot de passe d'application pour cette application

3. **Mettez à jour votre fichier .env**
   - Copiez le contenu de `env.example`
   - Remplacez les valeurs par vos nouvelles informations sécurisées

### Configuration Sécurisée

1. **Créez un fichier `.env` local** :
```bash
cp env.example .env
```

2. **Modifiez le fichier `.env` avec vos vraies informations** :
```env
SMTP_USERNAME=votre-nouveau-email@gmail.com
SMTP_PASSWORD=votre-nouveau-mot-de-passe-application
```

3. **Vérifiez que `.env` est dans `.gitignore`** :
```bash
echo ".env" >> .gitignore
```

### Bonnes Pratiques

- ✅ Utilisez toujours des fichiers `.env` pour les variables sensibles
- ✅ Ajoutez `.env` au `.gitignore`
- ✅ Utilisez des mots de passe d'application pour Gmail
- ✅ Changez régulièrement vos mots de passe
- ❌ Ne commitez jamais de vraies informations sensibles
- ❌ N'utilisez pas le mot de passe principal Gmail

### Vérification

Pour vérifier que tout est sécurisé :
```bash
git status
```
Vous ne devriez PAS voir `.env` dans les fichiers modifiés.

### Support

Si vous avez des questions sur la sécurité, consultez :
- [Documentation Google sur les mots de passe d'application](https://support.google.com/accounts/answer/185833)
- [Guide de sécurité des variables d'environnement](https://12factor.net/config) 