<?php
/**
 * Google Analytics 4 (gtag.js) — Google'ın resmi etiket kodu
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

if (!defined('HIVE_GA4_MEASUREMENT_ID')) {
    define('HIVE_GA4_MEASUREMENT_ID', 'G-J1DKY19WRL');
}

function hive_ga4_measurement_id() {
    if (defined('HIVE_GA4_MEASUREMENT_ID') && HIVE_GA4_MEASUREMENT_ID) {
        $const = trim(HIVE_GA4_MEASUREMENT_ID);
        if (preg_match('/^G-[A-Z0-9]+$/i', $const)) {
            return strtoupper($const);
        }
    }

    $id = get_option('hive_ga4_measurement_id', '');
    if (is_string($id) && $id !== '') {
        return strtoupper(trim($id));
    }

    if (is_multisite()) {
        $network = get_network_option(null, 'hive_ga4_measurement_id', '');
        if (is_string($network) && $network !== '') {
            return strtoupper(trim($network));
        }
    }

    return '';
}

/** Sayfa başına tek etiket (çift sayım önleme) */
function hive_ga4_tag_printed() {
    static $printed = false;
    if ($printed) {
        return true;
    }
    $printed = true;
    return false;
}

/**
 * Google'ın verdiği etiket — <head> hemen sonrası (header.php)
 */
function hive_ga4_render_tag() {
    if (hive_ga4_tag_printed()) {
        return;
    }

    $mid = hive_ga4_measurement_id();
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
}

function hive_ga4_sync_network_option($measurement_id) {
    if (!is_multisite()) {
        return;
    }
    $ga = is_string($measurement_id) ? strtoupper(trim($measurement_id)) : '';
    if ($ga === '' || !preg_match('/^G-[A-Z0-9]+$/i', $ga)) {
        return;
    }
    update_network_option(null, 'hive_ga4_measurement_id', $ga);
    foreach (get_sites(['number' => 500]) as $site) {
        switch_to_blog((int) $site->blog_id);
        update_option('hive_ga4_measurement_id', $ga, false);
        restore_current_blog();
    }
}

add_action('update_option_hive_ga4_measurement_id', function ($old, $new) {
    hive_ga4_sync_network_option($new);
}, 10, 2);
