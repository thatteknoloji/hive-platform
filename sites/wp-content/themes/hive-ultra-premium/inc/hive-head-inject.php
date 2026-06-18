<?php
/**
 * HIVE Head Inject — tüm sitelerde <head> hemen sonrası servis kodları
 * Google Analytics, GTM, Meta Pixel, site doğrulama, özel HTML
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

/** Tek seferlik çıktı (çift etiket önleme) */
function hive_head_inject_done() {
    static $done = false;
    if ($done) {
        return true;
    }
    $done = true;
    return false;
}

/**
 * Ağ geneli head injection listesi
 */
function hive_get_head_injections() {
    $raw = is_multisite()
        ? get_network_option(null, 'hive_head_injections', '')
        : get_option('hive_head_injections', '');

    if (is_array($raw)) {
        return $raw;
    }
    if (is_string($raw) && $raw !== '') {
        $decoded = json_decode($raw, true);
        if (is_array($decoded)) {
            return $decoded;
        }
    }

    return hive_default_head_injections();
}

function hive_default_head_injections() {
    $ga = function_exists('hive_ga4_measurement_id') ? hive_ga4_measurement_id() : 'G-J1DKY19WRL';
    return [
        [
            'id'       => 'ga4',
            'name'     => 'Google Analytics 4',
            'provider' => 'google_analytics',
            'enabled'  => true,
            'config'   => ['measurement_id' => $ga],
        ],
    ];
}

function hive_save_head_injections(array $items) {
    $json = wp_json_encode(array_values($items));
    if (is_multisite()) {
        update_network_option(null, 'hive_head_injections', $json);
        foreach (get_sites(['number' => 500]) as $site) {
            switch_to_blog((int) $site->blog_id);
            update_option('hive_head_injections', $json, false);
            restore_current_blog();
        }
    } else {
        update_option('hive_head_injections', $json);
    }
    return true;
}

/**
 * Sağlayıcıya göre resmi snippet üret
 */
function hive_render_provider_snippet(array $item) {
    $provider = $item['provider'] ?? 'custom';
    $config   = is_array($item['config'] ?? null) ? $item['config'] : [];

    switch ($provider) {
        case 'google_analytics':
            $mid = strtoupper(trim($config['measurement_id'] ?? ''));
            if (!$mid && function_exists('hive_ga4_measurement_id')) {
                $mid = hive_ga4_measurement_id();
            }
            if (!$mid || !preg_match('/^G-[A-Z0-9]+$/i', $mid)) {
                return;
            }
            ?>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=<?php echo esc_attr($mid); ?>"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', '<?php echo esc_js($mid); ?>');
</script>
            <?php
            break;

        case 'google_tag_manager':
            $cid = strtoupper(trim($config['container_id'] ?? ''));
            if (!$cid || !preg_match('/^GTM-[A-Z0-9]+$/i', $cid)) {
                return;
            }
            ?>
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','<?php echo esc_js($cid); ?>');</script>
<!-- End Google Tag Manager -->
            <?php
            break;

        case 'meta_pixel':
            $pid = preg_replace('/\D/', '', (string) ($config['pixel_id'] ?? ''));
            if (!$pid) {
                return;
            }
            ?>
<!-- Meta Pixel -->
<script>
!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,
document,'script','https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '<?php echo esc_js($pid); ?>');
fbq('track', 'PageView');
</script>
            <?php
            break;

        case 'google_site_verification':
            $token = sanitize_text_field($config['token'] ?? '');
            if (!$token) {
                return;
            }
            echo '<meta name="google-site-verification" content="' . esc_attr($token) . '" />' . "\n";
            break;

        case 'custom_html':
            $html = $item['html'] ?? '';
            if ($html === '') {
                return;
            }
            // HIVE panel kaynaklı — Google/Meta vb. resmi snippet'ler
            echo $html . "\n";
            break;
    }
}

/**
 * Tüm etkin injection'ları <head> başına bas
 */
function hive_render_head_injections() {
    if (hive_head_inject_done()) {
        return;
    }

    $items = hive_get_head_injections();
    if (!is_array($items)) {
        return;
    }

    foreach ($items as $item) {
        if (empty($item['enabled'])) {
            continue;
        }
        hive_render_provider_snippet($item);
    }
}
