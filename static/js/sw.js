self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (err) {
    data = { titulo: 'CUCU', mensaje: event.data ? event.data.text() : '' };
  }

  const title = data.titulo || 'CUCU';
  const options = {
    body: data.mensaje || '',
    icon: '/static/images/apple-touch-icon.png',
    badge: '/static/images/favicon-32.png',
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if ('focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow('/ui/notificaciones/');
      return undefined;
    })
  );
});
