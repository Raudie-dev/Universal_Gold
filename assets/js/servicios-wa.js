// Script para abrir WhatsApp con mensaje personalizado por servicio

document.addEventListener('DOMContentLoaded', function() {
  const servicios = [
    {
      selector: '.pillar-wa-reparacion',
      mensaje: '¡Hola! Me encantaría recibir información y una cotización para el servicio de restauración y reparación especializada de mis joyas. ✨',
    },
    {
      selector: '.pillar-wa-avaluo',
      mensaje: '¡Hola! Quisiera solicitar una cotización para un análisis o avalúo profesional de mis joyas. ✨',
    },
    {
      selector: '.pillar-wa-compra',
      mensaje: '¡Hola! Me gustaría consultar la tasa del día y el proceso para la venta de mi oro. Quedo atento a su información. 📈',
    },
    {
      selector: '.pillar-wa-personalizada',
      mensaje: '¡Hola! Me gustaría cotizar el diseño de una pieza personalizada y exclusiva. ¿Podrían asesorarme?',
    },
    {
      selector: '.pillar-wa-pulido',
      mensaje: '¡Hola! Me interesa devolverle el brillo original a mis piezas con su servicio de mantenimiento y pulido profesional. ✨',
    },
    {
      selector: '.pillar-wa-engaste',
      mensaje: '¡Hola! Quisiera cotizar el engaste de piedras preciosas para una joya especial. ¿Podrían indicarme los detalles del servicio? 💍',
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
