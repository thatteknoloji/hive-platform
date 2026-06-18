<?php
/**
 * 18+ yaş doğrulama kapısı — her oturumda bir kez
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Erken FOUC önleme — onay yoksa sayfa kilitli başlar
 */
function hive_age_gate_head_script() {
    if (is_admin()) {
        return;
    }
    ?>
    <script>
    (function () {
        try {
            if (sessionStorage.getItem('hive_age_verified') !== '1') {
                document.documentElement.classList.add('hive-age-pending');
            }
        } catch (e) {
            document.documentElement.classList.add('hive-age-pending');
        }
    })();
    </script>
    <?php
}
add_action('wp_head', 'hive_age_gate_head_script', 1);

/**
 * Script + i18n
 */
function hive_age_gate_assets() {
    if (is_admin()) {
        return;
    }

    wp_enqueue_script(
        'hive-age-gate',
        HIVE_ULTRA_URI . '/assets/js/age-gate.js',
        array(),
        HIVE_ULTRA_VERSION,
        true
    );

    wp_localize_script('hive-age-gate', 'hiveAgeGate', array(
        'storageKey' => 'hive_age_verified',
        'exitUrl'    => 'https://www.google.com/',
        'i18n'       => array(
            'title'       => __('Yaş Doğrulama', 'hive-ultra-premium'),
            'heading'     => __('Bu site yalnızca 18 yaş ve üzeri yetişkinler içindir.', 'hive-ultra-premium'),
            'body'        => __('Devam etmek için 18 yaşından büyük olduğunuzu onaylamanız gerekmektedir. Site içeriği yetişkinlere yöneliktir.', 'hive-ultra-premium'),
            'confirm'     => __('Evet, 18 yaşından büyüğüm', 'hive-ultra-premium'),
            'deny'        => __('Hayır, 18 yaşından küçüğüm', 'hive-ultra-premium'),
            'legalPrefix' => __('Devam ederek', 'hive-ultra-premium'),
            'legalTerms'  => __('Kullanım Şartları', 'hive-ultra-premium'),
            'legalAnd'    => __('ve', 'hive-ultra-premium'),
            'legalDisclaimer' => __('Sorumluluk Reddi', 'hive-ultra-premium'),
            'legalSuffix' => __('metinlerini kabul etmiş olursunuz.', 'hive-ultra-premium'),
        ),
        'legal' => array(
            'terms'       => hive_legal_page_url('kullanim-sartlari'),
            'disclaimer'  => hive_legal_page_url('sorumluluk-reddi'),
        ),
    ));
}
add_action('wp_enqueue_scripts', 'hive_age_gate_assets');

/**
 * Modal markup
 */
function hive_render_age_gate() {
    if (is_admin()) {
        return;
    }
    get_template_part('template-parts/age', 'gate');
}
add_action('wp_footer', 'hive_render_age_gate', 5);
