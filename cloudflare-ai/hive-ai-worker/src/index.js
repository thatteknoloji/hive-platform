export default {
  async fetch(request, env) {
    if (request.method !== 'POST') {
      return new Response(JSON.stringify({ error: 'Sadece POST isteği gönderin' }), {
        status: 405,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    try {
      const { prompt } = await request.json();

      if (!prompt) {
        return new Response(JSON.stringify({ error: 'Prompt gerekli' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      const response = await env.AI.run('@cf/meta/llama-3.1-8b-instruct', {
        messages: [
          { role: 'system', content: 'Sen yardımsever bir asistansın. Kısa ve net cevap ver.' },
          { role: 'user', content: prompt }
        ]
      });

      return new Response(JSON.stringify({
        success: true,
        response: response.response || response
      }), {
        headers: { 'Content-Type': 'application/json' }
      });

    } catch (error) {
      return new Response(JSON.stringify({
        success: false,
        error: error.message
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }
};
