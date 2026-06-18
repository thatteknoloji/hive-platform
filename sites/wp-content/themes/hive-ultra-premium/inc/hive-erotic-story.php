<?php
/**
 * Erotik Hikaye Arşivi – CPT + taxonomy + beğeni
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

add_action('init', 'hive_register_erotic_story');
function hive_register_erotic_story() {
    register_taxonomy('story_category', array('erotic_story'), array(
        'labels' => array(
            'name'          => __('Hikaye Kategorileri', 'hive-ultra-premium'),
            'singular_name' => __('Hikaye Kategorisi', 'hive-ultra-premium'),
        ),
        'hierarchical'      => true,
        'public'            => true,
        'show_admin_column' => true,
        'rewrite'           => array('slug' => 'hikaye-kategori'),
        'show_in_rest'      => true,
    ));

    register_post_type('erotic_story', array(
        'labels' => array(
            'name'          => __('Erotik Hikayeler', 'hive-ultra-premium'),
            'singular_name' => __('Erotik Hikaye', 'hive-ultra-premium'),
            'add_new_item'  => __('Yeni Hikaye Ekle', 'hive-ultra-premium'),
            'archives'      => __('Hikaye Arşivi', 'hive-ultra-premium'),
        ),
        'public'              => true,
        'has_archive'         => true,
        'rewrite'             => array('slug' => 'hikaye'),
        'menu_icon'           => 'dashicons-book-alt',
        'supports'            => array('title', 'editor', 'thumbnail', 'excerpt', 'comments'),
        'show_in_rest'        => true,
        'taxonomies'          => array('story_category'),
    ));
}

add_action('add_meta_boxes', 'hive_erotic_story_metabox');
function hive_erotic_story_metabox() {
    add_meta_box(
        'hive_erotic_story_meta',
        __('Hikaye Lokasyonu', 'hive-ultra-premium'),
        'hive_erotic_story_metabox_cb',
        'erotic_story',
        'side',
        'default'
    );
}

function hive_erotic_story_metabox_cb($post) {
    wp_nonce_field('hive_erotic_story_save', 'hive_erotic_story_nonce');
    $lokasyon = get_post_meta($post->ID, 'story_lokasyon', true);
    echo '<label for="story_lokasyon">' . esc_html__('Lokasyon', 'hive-ultra-premium') . '</label>';
    echo '<input type="text" id="story_lokasyon" name="story_lokasyon" value="' . esc_attr($lokasyon) . '" style="width:100%;margin-top:6px;" placeholder="Kuşadası, Kadınlar Denizi">';
}

add_action('save_post_erotic_story', 'hive_save_erotic_story_meta');
function hive_save_erotic_story_meta($post_id) {
    if (!isset($_POST['hive_erotic_story_nonce']) || !wp_verify_nonce($_POST['hive_erotic_story_nonce'], 'hive_erotic_story_save')) {
        return;
    }
    if (defined('DOING_AUTOSAVE') && DOING_AUTOSAVE || !current_user_can('edit_post', $post_id)) {
        return;
    }
    if (isset($_POST['story_lokasyon'])) {
        update_post_meta($post_id, 'story_lokasyon', sanitize_text_field($_POST['story_lokasyon']));
    }
}

/**
 * Beğeni sayacı
 */
function hive_story_likes($post_id = null) {
    $post_id = $post_id ?: get_the_ID();
    return (int) get_post_meta($post_id, 'story_likes', true);
}

add_action('wp_ajax_hive_story_like', 'hive_ajax_story_like');
add_action('wp_ajax_nopriv_hive_story_like', 'hive_ajax_story_like');
function hive_ajax_story_like() {
    check_ajax_referer('hive_ultra_nonce', 'nonce');
    $post_id = isset($_POST['post_id']) ? (int) $_POST['post_id'] : 0;
    if (!$post_id || get_post_type($post_id) !== 'erotic_story') {
        wp_send_json_error();
    }
    $likes = hive_story_likes($post_id) + 1;
    update_post_meta($post_id, 'story_likes', $likes);
    wp_send_json_success(array('likes' => $likes));
}

function hive_render_story_like_button($post_id = null) {
    $post_id = $post_id ?: get_the_ID();
    $likes   = hive_story_likes($post_id);
    echo '<button type="button" class="story-like-btn" data-story-id="' . esc_attr($post_id) . '" aria-label="' . esc_attr__('Beğen', 'hive-ultra-premium') . '">';
    echo '❤️ <span class="story-like-count">' . esc_html($likes) . '</span>';
    echo '</button>';
}

/**
 * Varsayılan kategorileri oluştur
 */
function hive_seed_story_categories() {
    if (get_option('hive_story_cats_seeded')) {
        return;
    }
    $cats = array(
        'anal-hikaye'  => 'Anal Escort Hikayeleri',
        'oral-hikaye'  => 'Oral Escort Hikayeleri',
        'vip-hikaye'   => 'VIP Escort Hikayeleri',
        'otel-hikaye'  => 'Otel Escort Hikayeleri',
        'plaj-hikaye'  => 'Plaj Escort Hikayeleri',
        'gece-hikaye'  => 'Gece Escort Hikayeleri',
        'cift-hikaye'  => 'Çift Escort Hikayeleri',
        'grup-hikaye'  => 'Grup Escort Hikayeleri',
    );
    foreach ($cats as $slug => $name) {
        if (!term_exists($slug, 'story_category')) {
            wp_insert_term($name, 'story_category', array('slug' => $slug));
        }
    }
    update_option('hive_story_cats_seeded', 1);
}
add_action('init', 'hive_seed_story_categories', 20);

add_filter('pre_get_document_title', 'hive_erotic_story_title');
function hive_erotic_story_title($title) {
    if (is_singular('erotic_story')) {
        $loc = get_post_meta(get_the_ID(), 'story_lokasyon', true);
        $cat = get_the_terms(get_the_ID(), 'story_category');
        $cat_name = ($cat && !is_wp_error($cat)) ? $cat[0]->name : '';
        return get_the_title() . ($cat_name ? ' – ' . $cat_name : '') . ' | Bal Kutusu';
    }
    if (is_tax('story_category')) {
        return single_term_title('', false) . ' | Bal Kutusu Hikaye Arşivi';
    }
    if (is_post_type_archive('erotic_story')) {
        return __('Erotik Hikaye Arşivi', 'hive-ultra-premium') . ' | Bal Kutusu';
    }
    return $title;
}

add_action('wp_head', 'hive_erotic_story_schema', 8);
function hive_erotic_story_schema() {
    if (!is_singular('erotic_story')) {
        return;
    }
    $loc = get_post_meta(get_the_ID(), 'story_lokasyon', true);
    ?>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": <?php echo wp_json_encode(get_the_title()); ?>,
  "description": <?php echo wp_json_encode(wp_strip_all_tags(get_the_excerpt() ?: get_the_content())); ?>,
  "datePublished": "<?php echo esc_attr(get_the_date('c')); ?>",
  "author": {"@type": "Organization", "name": "Bal Kutusu"},
  <?php if ($loc) : ?>
  "contentLocation": {"@type": "Place", "name": <?php echo wp_json_encode($loc); ?>, "address": {"@type": "PostalAddress", "addressLocality": "Kuşadası", "addressCountry": "TR"}},
  <?php endif; ?>
  "publisher": {"@type": "Organization", "name": "Bal Kutusu", "url": "<?php echo esc_url(home_url('/')); ?>"}
}
</script>
    <?php
}
