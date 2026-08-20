// Traduction côté client : le serveur sérialise le catalogue de la langue active dans
// window.HOMEPORT_I18N (voir les templates). T(clé, {variables}) — clé absente : la clé nue,
// visible immédiatement en développement. Tn : pluriel par paires _one/_many.
window.T = (key, vars) => {
  let s = (window.HOMEPORT_I18N || {})[key] || key;
  for (const [name, value] of Object.entries(vars || {})) {
    s = s.replaceAll(`{${name}}`, value);
  }
  return s;
};
window.Tn = (key, count, vars) =>
  window.T(`${key}${count === 1 ? '_one' : '_many'}`, { count, ...vars });
