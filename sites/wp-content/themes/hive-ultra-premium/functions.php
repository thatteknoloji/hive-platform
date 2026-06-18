<?php
/**
 * Hive Ultra Premium Plus functions and definitions
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

define('HIVE_ULTRA_VERSION', '2.0.2');
define('HIVE_ULTRA_DIR', get_template_directory());
define('HIVE_ULTRA_URI', get_template_directory_uri());

require_once HIVE_ULTRA_DIR . '/inc/hive-maps.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-categories-nav.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-category-menu.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-seo.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-video.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-story.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-erotic-story.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-network.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-main-feed.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-escort-variations.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-seo-content.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-swipe.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-legal.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-age-gate.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-gece-hayati.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-unified-search.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-analytics.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-head-inject.php';
require_once HIVE_ULTRA_DIR . '/inc/hive-index-recovery.php';

/**
 * Theme setup
 */
function hive_ultra_setup() {
    load_theme_textdomain('hive-ultra-premium', HIVE_ULTRA_DIR . '/languages');

    add_theme_support('automatic-feed-links');
    add_theme_support('title-tag');
    add_theme_support('post-thumbnails');
    add_theme_support('custom-logo', array(
        'height'      => 80,
        'width'       => 240,
        'flex-height' => true,
        'flex-width'  => true,
    ));
    add_theme_support('html5', array(
        'search-form', 'comment-form', 'comment-list', 'gallery', 'caption', 'style', 'script',
    ));
    add_theme_support('customize-selective-refresh-widgets');

    add_image_size('hive-profile-card', 560, 420, true);
    add_image_size('hive-profile-thumb', 200, 200, true);

    register_nav_menus(array(
        'primary' => __('Ana Menü', 'hive-ultra-premium'),
        'footer'  => __('Footer Menü', 'hive-ultra-premium'),
    ));
}
add_action('after_setup_theme', 'hive_ultra_setup');

/**
 * Register widget areas
 */
function hive_ultra_widgets_init() {
    for ($i = 1; $i <= 3; $i++) {
        register_sidebar(array(
            'name'          => sprintf(__('Footer Alan %d', 'hive-ultra-premium'), $i),
            'id'            => 'footer-' . $i,
            'description'   => sprintf(__('Footer widget alanı %d', 'hive-ultra-premium'), $i),
            'before_widget' => '<div id="%1$s" class="footer-widget %2$s">',
            'after_widget'  => '</div>',
            'before_title'  => '<h3 class="widget-title">',
            'after_title'   => '</h3>',
        ));
    }
}
add_action('widgets_init', 'hive_ultra_widgets_init');

/**
 * Enqueue scripts and styles
 */
function hive_ultra_scripts() {
    wp_enqueue_style(
        'hive-ultra-fonts',
        'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Poppins:wght@500;600;700&display=swap',
        array(),
        null
    );

    wp_enqueue_style(
        'hive-ultra-style',
        get_stylesheet_uri(),
        array('hive-ultra-fonts'),
        HIVE_ULTRA_VERSION
    );

    wp_enqueue_style(
        'hive-ultra-theme-polish',
        HIVE_ULTRA_URI . '/assets/css/hive-theme-polish.css',
        array('hive-ultra-style'),
        HIVE_ULTRA_VERSION
    );

    wp_enqueue_script(
        'hive-ultra-main',
        HIVE_ULTRA_URI . '/assets/js/main.js',
        array(),
        HIVE_ULTRA_VERSION,
        true
    );

    wp_localize_script('hive-ultra-main', 'hiveUltra', array(
        'ajaxUrl'    => admin_url('admin-ajax.php'),
        'nonce'      => wp_create_nonce('hive_ultra_nonce'),
        'searchUrl'  => home_url('/'),
        'searchI18n' => array(
            'placeholder' => __('İlan adı, kullanıcı adı, kategori, lokasyon…', 'hive-ultra-premium'),
            'empty'       => __('Sonuç bulunamadı', 'hive-ultra-premium'),
            'more'        => __('Tüm sonuçları gör', 'hive-ultra-premium'),
            'loading'     => __('Aranıyor…', 'hive-ultra-premium'),
        ),
    ));
}
add_action('wp_enqueue_scripts', 'hive_ultra_scripts');

/**
 * Register Custom Post Type: companion_profile
 */
function hive_ultra_register_cpt() {
    $labels = array(
        'name'               => __('Profiller', 'hive-ultra-premium'),
        'singular_name'      => __('Profil', 'hive-ultra-premium'),
        'menu_name'          => __('Profiller', 'hive-ultra-premium'),
        'add_new'            => __('Yeni Ekle', 'hive-ultra-premium'),
        'add_new_item'       => __('Yeni Profil Ekle', 'hive-ultra-premium'),
        'edit_item'          => __('Profili Düzenle', 'hive-ultra-premium'),
        'new_item'           => __('Yeni Profil', 'hive-ultra-premium'),
        'view_item'          => __('Profili Görüntüle', 'hive-ultra-premium'),
        'search_items'       => __('Profil Ara', 'hive-ultra-premium'),
        'not_found'          => __('Profil bulunamadı', 'hive-ultra-premium'),
        'not_found_in_trash' => __('Çöp kutusunda profil yok', 'hive-ultra-premium'),
    );

    register_post_type('companion_profile', array(
        'labels'              => $labels,
        'public'              => true,
        'has_archive'         => true,
        'rewrite'             => array('slug' => 'profil'),
        'menu_icon'           => 'dashicons-groups',
        'supports'            => array('title', 'editor', 'thumbnail', 'excerpt'),
        'show_in_rest'        => true,
        'exclude_from_search' => false,
    ));
}
add_action('init', 'hive_ultra_register_cpt');

/**
 * Register Custom Taxonomy: companion_category
 */
function hive_ultra_register_taxonomy() {
    $labels = array(
        'name'          => __('Kategoriler', 'hive-ultra-premium'),
        'singular_name' => __('Kategori', 'hive-ultra-premium'),
        'search_items'  => __('Kategori Ara', 'hive-ultra-premium'),
        'all_items'     => __('Tüm Kategoriler', 'hive-ultra-premium'),
        'edit_item'     => __('Kategoriyi Düzenle', 'hive-ultra-premium'),
        'add_new_item'  => __('Yeni Kategori Ekle', 'hive-ultra-premium'),
    );

    register_taxonomy('companion_category', array('companion_profile'), array(
        'labels'            => $labels,
        'hierarchical'      => true,
        'public'            => true,
        'show_admin_column' => true,
        'rewrite'           => array('slug' => 'kategori'),
        'show_in_rest'      => true,
    ));
}
add_action('init', 'hive_ultra_register_taxonomy');

/**
 * Meta box for profile fields
 */
function hive_ultra_add_meta_boxes() {
    add_meta_box(
        'hive_profile_details',
        __('Profil Bilgileri', 'hive-ultra-premium'),
        'hive_ultra_meta_box_callback',
        'companion_profile',
        'normal',
        'high'
    );
}
add_action('add_meta_boxes', 'hive_ultra_add_meta_boxes');

function hive_ultra_meta_box_callback($post) {
    wp_nonce_field('hive_ultra_save_meta', 'hive_ultra_meta_nonce');

    $fields = array(
        'yas'          => __('Yaş', 'hive-ultra-premium'),
        'telefon'      => __('Telefon', 'hive-ultra-premium'),
        'telegram'          => __('Telegram Kullanıcı Adı', 'hive-ultra-premium'),
        'telegram_chat_id'  => __('Telegram Chat ID (teklif bildirimi)', 'hive-ultra-premium'),
        'lokasyon'          => __('Lokasyon', 'hive-ultra-premium'),
        'fiyat'        => __('Fiyat (₺)', 'hive-ultra-premium'),
        'odeme_sekli'  => __('Ödeme Şekli', 'hive-ultra-premium'),
        'ozellikler'   => __('Özellikler', 'hive-ultra-premium'),
    );

    echo '<table class="form-table">';
    foreach ($fields as $key => $label) {
        $value = get_post_meta($post->ID, $key, true);
        echo '<tr><th><label for="hive_' . esc_attr($key) . '">' . esc_html($label) . '</label></th>';
        echo '<td><input type="text" id="hive_' . esc_attr($key) . '" name="hive_' . esc_attr($key) . '" value="' . esc_attr($value) . '" class="regular-text" /></td></tr>';
    }

    $vip = get_post_meta($post->ID, 'vip', true);
    echo '<tr><th><label for="hive_vip">' . esc_html__('VIP Profil', 'hive-ultra-premium') . '</label></th>';
    echo '<td><input type="checkbox" id="hive_vip" name="hive_vip" value="1" ' . checked($vip, '1', false) . ' /> ';
    echo '<span class="description">' . esc_html__('VIP bölümünde göster', 'hive-ultra-premium') . '</span></td></tr>';
    echo '</table>';
}

function hive_ultra_save_meta($post_id) {
    if (!isset($_POST['hive_ultra_meta_nonce']) || !wp_verify_nonce($_POST['hive_ultra_meta_nonce'], 'hive_ultra_save_meta')) {
        return;
    }
    if (defined('DOING_AUTOSAVE') && DOING_AUTOSAVE) {
        return;
    }
    if (!current_user_can('edit_post', $post_id)) {
        return;
    }

    $text_fields = array('yas', 'telefon', 'telegram', 'telegram_chat_id', 'lokasyon', 'fiyat', 'odeme_sekli', 'ozellikler');
    foreach ($text_fields as $field) {
        if (isset($_POST['hive_' . $field])) {
            $val = sanitize_text_field($_POST['hive_' . $field]);
            if ($field === 'telegram') {
                $val = ltrim(str_replace('@', '', $val), '/');
            }
            update_post_meta($post_id, $field, $val);
        }
    }

    $vip = isset($_POST['hive_vip']) ? '1' : '0';
    update_post_meta($post_id, 'vip', $vip);
}
add_action('save_post_companion_profile', 'hive_ultra_save_meta');

/**
 * Admin columns for profile list
 */
function hive_ultra_admin_columns($columns) {
    $new = array();
    foreach ($columns as $key => $label) {
        $new[$key] = $label;
        if ($key === 'title') {
            $new['yas']      = __('Yaş', 'hive-ultra-premium');
            $new['telefon']  = __('Telefon', 'hive-ultra-premium');
            $new['lokasyon'] = __('Lokasyon', 'hive-ultra-premium');
            $new['fiyat']    = __('Fiyat', 'hive-ultra-premium');
            $new['vip']      = __('VIP', 'hive-ultra-premium');
        }
    }
    return $new;
}
add_filter('manage_companion_profile_posts_columns', 'hive_ultra_admin_columns');

function hive_ultra_admin_column_content($column, $post_id) {
    switch ($column) {
        case 'yas':
        case 'telefon':
        case 'lokasyon':
        case 'fiyat':
            echo esc_html(get_post_meta($post_id, $column, true));
            break;
        case 'vip':
            echo get_post_meta($post_id, 'vip', true) === '1' ? '⭐' : '—';
            break;
    }
}
add_action('manage_companion_profile_posts_custom_column', 'hive_ultra_admin_column_content', 10, 2);

/**
 * Helper: get profile meta with fallback
 */
function hive_ultra_get_meta($post_id, $key, $default = '') {
    $value = get_post_meta($post_id, $key, true);
    return $value !== '' ? $value : $default;
}

/**
 * Helper: profile placeholder image URL
 */
function hive_ultra_placeholder_url() {
    return HIVE_ULTRA_URI . '/assets/images/placeholder.svg';
}

/**
 * Bal Kutusu marka görselleri (tüm subdomainlerde aynı tema yolu)
 */
function hive_brand_logo_url() {
    return HIVE_ULTRA_URI . '/assets/images/bal-kutusu-logo.png';
}

function hive_brand_favicon_url() {
    return HIVE_ULTRA_URI . '/assets/images/favicon.png';
}

function hive_brand_apple_icon_url() {
    return HIVE_ULTRA_URI . '/assets/images/apple-touch-icon.png';
}

/**
 * Favicon + PWA ikon — network geneli
 */
function hive_brand_head_icons() {
    $fav   = hive_brand_favicon_url();
    $apple = hive_brand_apple_icon_url();
    $logo  = hive_brand_logo_url();
    echo '<link rel="icon" type="image/png" sizes="32x32" href="' . esc_url($fav) . '">' . "\n";
    echo '<link rel="icon" type="image/png" sizes="192x192" href="' . esc_url($fav) . '">' . "\n";
    echo '<link rel="apple-touch-icon" sizes="180x180" href="' . esc_url($apple) . '">' . "\n";
    echo '<meta name="msapplication-TileImage" content="' . esc_url($fav) . '">' . "\n";
    if (is_front_page() || (function_exists('hive_is_main_site') && hive_is_main_site())) {
        echo '<meta property="og:image" content="' . esc_url($logo) . '">' . "\n";
    }
}
add_action('wp_head', 'hive_brand_head_icons', 1);

/**
 * Include template parts helper
 */
function hive_ultra_get_profile_card($post = null) {
    get_template_part('template-parts/profile', 'card', array('post' => $post));
}

function hive_ultra_get_profile_row($post = null) {
    get_template_part('template-parts/profile', 'row', array('post' => $post));
}

/**
 * Search only companion profiles on front-end search
 */
/* Arama filtresi: inc/hive-unified-search.php (companion_profile + meta + kategori) */

/**
 * Profil arşivi — 10'lu satırlar (sayfa başına 20)
 */
function hive_ultra_archive_posts_per_page($query) {
    if (is_admin() || !$query->is_main_query()) {
        return;
    }
    if ($query->is_post_type_archive('companion_profile') || $query->is_tax('companion_category')) {
        $query->set('posts_per_page', 20);
    }
}
add_action('pre_get_posts', 'hive_ultra_archive_posts_per_page');

/**
 * Flush rewrite rules on theme activation
 */
function hive_ultra_activation() {
    hive_ultra_register_cpt();
    hive_ultra_register_taxonomy();
    if (function_exists('hive_register_gece_hayati')) {
        hive_register_gece_hayati();
    }
    flush_rewrite_rules();
}
add_action('after_switch_theme', 'hive_ultra_activation');

/**
 * Lazy-load images + decoding async (performans)
 */
function hive_ultra_lazy_load_attrs($attr, $attachment, $size) {
    if (empty($attr['loading'])) {
        $attr['loading'] = 'lazy';
    }
    if (empty($attr['decoding'])) {
        $attr['decoding'] = 'async';
    }
    return $attr;
}
add_filter('wp_get_attachment_image_attributes', 'hive_ultra_lazy_load_attrs', 10, 3);

/**
 * Telegram link helper
 */
function hive_ultra_telegram_url($username) {
    $username = ltrim(str_replace('@', '', (string) $username), '/');
    return $username ? 'https://t.me/' . rawurlencode($username) : '';
}

/**
 * SEO title filter
 */
function hive_custom_document_title($title) {
    if (is_front_page()) {
        return 'Kuşadası Escort – En İyi VIP Model Escort Bayanlar | Bal Kutusu';
    }
    if (is_singular('companion_profile')) {
        return get_the_title() . ' – Kuşadası Escort | Bal Kutusu';
    }
    if (is_tax('companion_category')) {
        return single_term_title('', false) . ' Escort Kuşadası | Bal Kutusu';
    }
    return $title;
}
add_filter('pre_get_document_title', 'hive_custom_document_title');

/**
 * Customizer — ilan yayınlama iletişim telefonu
 */
function hive_ultra_customize_register($wp_customize) {
    $wp_customize->add_section('hive_contact', array(
        'title'    => __('İletişim', 'hive-ultra-premium'),
        'priority' => 120,
    ));
    $wp_customize->add_setting('hive_ilan_contact_phone', array(
        'default'           => '0xxx xxx xx xx',
        'sanitize_callback' => 'sanitize_text_field',
    ));
    $wp_customize->add_control('hive_ilan_contact_phone', array(
        'label'       => __('İlan yayınlama telefonu (hero)', 'hive-ultra-premium'),
        'description' => __('Ana sayfa hero bandında görünen numara.', 'hive-ultra-premium'),
        'section'     => 'hive_contact',
        'type'        => 'text',
    ));
}
add_action('customize_register', 'hive_ultra_customize_register');
