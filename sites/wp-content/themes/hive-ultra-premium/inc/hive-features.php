<?php
/**
 * Theme features: AJAX, schema, view count, ratings, helpers
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

/** Kuşadası mahalle listesi */
function hive_ultra_locations() {
    return array(
        'Kadınlar Denizi', 'Yılancı Burnu', 'Güvercinada', 'Davutlar', 'Merkez',
        'Türkmen', 'Cumhuriyet', 'Hacıfeyzullah', 'Camiatik', 'Karaova',
        'Güzelçamlı', 'Yavansu', 'Soğucak', 'Çamlık', 'Kuştur', 'Aydınlı', 'Pamucak',
    );
}

/** Tutarlı çevrimiçi durumu (post ID'ye göre) */
function hive_ultra_is_online($post_id) {
    $manual = get_post_meta($post_id, 'online_status', true);
    if ($manual === 'online') {
        return true;
    }
    if ($manual === 'offline') {
        return false;
    }
    return ($post_id % 3) !== 0;
}

/** Profil görüntülenme sayacı */
function hive_track_profile_view($post_id) {
    if (get_post_type($post_id) !== 'companion_profile') {
        return;
    }
    $count = (int) get_post_meta($post_id, 'view_count', true);
    update_post_meta($post_id, 'view_count', $count + 1);
}

add_action('wp', function () {
    if (is_singular('companion_profile')) {
        hive_track_profile_view(get_queried_object_id());
    }
});

/** Yorum desteği + puanlama */
add_action('init', function () {
    add_post_type_support('companion_profile', 'comments');
});

function hive_ultra_save_comment_rating($comment_id) {
    if (isset($_POST['hive_rating']) && is_numeric($_POST['hive_rating'])) {
        $rating = max(1, min(5, (int) $_POST['hive_rating']));
        add_comment_meta($comment_id, 'hive_rating', $rating, true);
    }
}
add_action('comment_post', 'hive_ultra_save_comment_rating');

function hive_ultra_comment_rating($comment_id) {
    return (int) get_comment_meta($comment_id, 'hive_rating', true);
}

/** Breadcrumb */
function hive_ultra_breadcrumb() {
    get_template_part('template-parts/breadcrumb');
}

/** Schema JSON-LD */
function hive_ultra_schema_markup() {
    if (!is_singular('companion_profile')) {
        return;
    }
    $id = get_the_ID();
    $schema = array(
        '@context'    => 'https://schema.org',
        '@type'       => 'Person',
        'name'        => get_the_title(),
        'description' => wp_strip_all_tags(get_the_excerpt() ?: get_the_content()),
        'url'         => get_permalink(),
        'address'     => array(
            '@type'           => 'PostalAddress',
            'addressLocality' => hive_ultra_get_meta($id, 'lokasyon', 'Kuşadası'),
            'addressCountry'  => 'TR',
        ),
    );
    if (has_post_thumbnail()) {
        $schema['image'] = get_the_post_thumbnail_url($id, 'large');
    }
    echo '<script type="application/ld+json">' . wp_json_encode($schema, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . '</script>';
}
add_action('wp_head', 'hive_ultra_schema_markup', 5);

/** Breadcrumb schema */
function hive_ultra_breadcrumb_schema() {
    if (!is_singular('companion_profile') && !is_post_type_archive('companion_profile')) {
        return;
    }
    $items = array(
        array('@type' => 'ListItem', 'position' => 1, 'name' => 'Ana Sayfa', 'item' => home_url('/')),
        array('@type' => 'ListItem', 'position' => 2, 'name' => 'Profiller', 'item' => get_post_type_archive_link('companion_profile')),
    );
    if (is_singular('companion_profile')) {
        $items[] = array('@type' => 'ListItem', 'position' => 3, 'name' => get_the_title(), 'item' => get_permalink());
    }
    $schema = array(
        '@context'        => 'https://schema.org',
        '@type'           => 'BreadcrumbList',
        'itemListElement' => $items,
    );
    echo '<script type="application/ld+json">' . wp_json_encode($schema, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . '</script>';
}
add_action('wp_head', 'hive_ultra_breadcrumb_schema', 6);

/** WP_Query args from filter request */
function hive_ultra_build_query_args($params = array()) {
    $args = array(
        'post_type'      => 'companion_profile',
        'posts_per_page' => isset($params['per_page']) ? (int) $params['per_page'] : 12,
        'post_status'    => 'publish',
    );

    $meta_query = array('relation' => 'AND');

    if (!empty($params['profil_tipi'])) {
        $meta_query[] = array(
            'key'   => 'profil_tipi',
            'value' => sanitize_text_field($params['profil_tipi']),
        );
    }

    if (!empty($params['lokasyon'])) {
        $meta_query[] = array(
            'key'     => 'lokasyon',
            'value'   => sanitize_text_field($params['lokasyon']),
            'compare' => 'LIKE',
        );
    }

    if (isset($params['yas_min']) && $params['yas_min'] !== '') {
        $meta_query[] = array(
            'key'     => 'yas',
            'type'    => 'NUMERIC',
            'compare' => 'BETWEEN',
            'value'   => array(
                (int) $params['yas_min'],
                (int) ($params['yas_max'] ?? 99),
            ),
        );
    }
    if (isset($params['fiyat_min']) && $params['fiyat_min'] !== '') {
        $meta_query[] = array(
            'key'     => 'fiyat',
            'type'    => 'NUMERIC',
            'compare' => 'BETWEEN',
            'value'   => array(
                (int) $params['fiyat_min'],
                (int) ($params['fiyat_max'] ?? 99999),
            ),
        );
    }
    if (count($meta_query) > 1) {
        $args['meta_query'] = $meta_query;
    }

    $sort = sanitize_text_field($params['sort'] ?? 'newest');
    switch ($sort) {
        case 'cheapest':
            $args['meta_key'] = 'fiyat';
            $args['orderby']  = 'meta_value_num';
            $args['order']    = 'ASC';
            break;
        case 'expensive':
            $args['meta_key'] = 'fiyat';
            $args['orderby']  = 'meta_value_num';
            $args['order']    = 'DESC';
            break;
        case 'popular':
            $args['meta_key'] = 'view_count';
            $args['orderby']  = 'meta_value_num';
            $args['order']    = 'DESC';
            break;
        case 'newest':
        default:
            $args['orderby'] = 'date';
            $args['order']   = 'DESC';
            break;
    }

    if (!empty($params['ids'])) {
        $ids = array_map('intval', explode(',', $params['ids']));
        $args['post__in'] = $ids;
        $args['orderby']  = 'post__in';
    }

    return $args;
}

/** Render profiles HTML */
function hive_ultra_render_profiles_html($query, $layout = 'row') {
    ob_start();
    if ($query->have_posts()) {
        if ($layout === 'card') {
            echo '<div class="slide-track">';
            while ($query->have_posts()) {
                $query->the_post();
                hive_ultra_get_profile_card(get_post());
            }
            echo '</div>';
        } else {
            echo '<div class="profiles-list">';
            while ($query->have_posts()) {
                $query->the_post();
                hive_ultra_get_profile_row(get_post());
            }
            echo '</div>';
        }
        wp_reset_postdata();
    } else {
        echo '<div class="no-results"><p>' . esc_html__('Kriterlere uygun profil bulunamadı.', 'hive-ultra-premium') . '</p></div>';
    }
    return ob_get_clean();
}

/** AJAX: filter profiles */
function hive_ultra_ajax_filter() {
    check_ajax_referer('hive_ultra_nonce', 'nonce');
    $params = array(
        'yas_min'     => $_POST['yas_min'] ?? '',
        'yas_max'     => $_POST['yas_max'] ?? '',
        'fiyat_min'   => $_POST['fiyat_min'] ?? '',
        'fiyat_max'   => $_POST['fiyat_max'] ?? '',
        'lokasyon'    => $_POST['lokasyon'] ?? '',
        'sort'        => $_POST['sort'] ?? 'newest',
        'profil_tipi' => $_POST['profil_tipi'] ?? '',
        'per_page'    => $_POST['per_page'] ?? 24,
        'layout'      => $_POST['layout'] ?? 'row',
    );
    $layout = sanitize_text_field($params['layout']);
    $query  = new WP_Query(hive_ultra_build_query_args($params));
    wp_send_json_success(array(
        'html'  => hive_ultra_render_profiles_html($query, $layout),
        'count' => $query->found_posts,
    ));
}
add_action('wp_ajax_hive_filter_profiles', 'hive_ultra_ajax_filter');
add_action('wp_ajax_nopriv_hive_filter_profiles', 'hive_ultra_ajax_filter');

/** AJAX: favorites by IDs */
function hive_ultra_ajax_favorites() {
    check_ajax_referer('hive_ultra_nonce', 'nonce');
    $ids = sanitize_text_field($_POST['ids'] ?? '');
    if (!$ids) {
        wp_send_json_success(array('html' => '<div class="no-results"><p>' . esc_html__('Henüz favori profil yok.', 'hive-ultra-premium') . '</p></div>'));
    }
    $query = new WP_Query(hive_ultra_build_query_args(array('ids' => $ids, 'per_page' => 50)));
    wp_send_json_success(array('html' => hive_ultra_render_profiles_html($query, 'row')));
}
add_action('wp_ajax_hive_get_favorites', 'hive_ultra_ajax_favorites');
add_action('wp_ajax_nopriv_hive_get_favorites', 'hive_ultra_ajax_favorites');

/** Localize script data */
function hive_ultra_localize_script() {
    wp_localize_script('hive-ultra-main', 'hiveUltra', array(
        'ajaxUrl'   => admin_url('admin-ajax.php'),
        'nonce'     => wp_create_nonce('hive_ultra_nonce'),
        'homeUrl'   => home_url('/'),
        'archiveUrl'=> get_post_type_archive_link('companion_profile'),
        'whatsapp'  => get_theme_mod('hive_whatsapp_number', '905555555555'),
    ));
}
add_action('wp_enqueue_scripts', 'hive_ultra_localize_script', 20);

/** Custom comment list item with stars */
function hive_ultra_comment_callback($comment, $args, $depth) {
    $rating = hive_ultra_comment_rating($comment->comment_ID);
    ?>
    <li <?php comment_class('hive-comment-item'); ?> id="comment-<?php comment_ID(); ?>">
        <article class="hive-comment-body">
            <header class="hive-comment-header">
                <strong class="hive-comment-author"><?php comment_author(); ?></strong>
                <?php if ($rating) : ?>
                    <span class="hive-comment-stars" aria-label="<?php echo esc_attr($rating . '/5'); ?>">
                        <?php echo str_repeat('★', $rating) . str_repeat('☆', 5 - $rating); ?>
                    </span>
                <?php endif; ?>
                <time datetime="<?php comment_time('c'); ?>" class="hive-comment-date"><?php comment_date(); ?></time>
            </header>
            <div class="hive-comment-content"><?php comment_text(); ?></div>
        </article>
    <?php
}

/** Theme customizer: site WhatsApp */
function hive_ultra_customize_register($wp_customize) {
    $wp_customize->add_section('hive_contact', array(
        'title'    => __('Hive İletişim', 'hive-ultra-premium'),
        'priority' => 130,
    ));
    $wp_customize->add_setting('hive_whatsapp_number', array(
        'default'           => '905555555555',
        'sanitize_callback' => 'sanitize_text_field',
    ));
    $wp_customize->add_control('hive_whatsapp_number', array(
        'label'   => __('Site WhatsApp Numarası (905...)', 'hive-ultra-premium'),
        'section' => 'hive_contact',
        'type'    => 'text',
    ));
}
add_action('customize_register', 'hive_ultra_customize_register');
