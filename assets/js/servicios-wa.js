// Script para abrir WhatsApp con mensaje personalizado por servicio

document.addEventListener('DOMContentLoaded', function() {
  const servicios = [
    {
      selector: '.pillar-wa-reparacion',
      mensaje: 'Hola, me interesa solicitar reparación de joyas.',
    },
    {
      selector: '.pillar-wa-avaluo',
      mensaje: 'Hola, me interesa un análisis y avalúo de prendas.',
    },
    {
      selector: '.pillar-wa-compra',
      mensaje: 'Hola, me interesa vender o comprar oro.',
    },
    {
      selector: '.pillar-wa-personalizada',
      mensaje: 'Hola, quiero personalizar una joya.',
    },
    {
      selector: '.pillar-wa-pulido',
      mensaje: 'Hola, quiero pulir mis joyas.',
    },
    {
      selector: '.pillar-wa-engaste',
      mensaje: 'Hola, quiero engastar piedras en una joya.',
    },
  ];

  // El número se inyecta desde Django en window.WHATSAPP_EMPRESA
  const telefono = window.WHATSAPP_EMPRESA;

  servicios.forEach(servicio => {
    document.querySelectorAll(servicio.selector).forEach(el => {
      el.addEventListener('click', function(e) {
        e.preventDefault();
        if (!telefono) return;
        const url = `https://wa.me/${telefono}?text=${encodeURIComponent(servicio.mensaje)}`;
        window.open(url, '_blank');
      });
    });
  });
});
