<?php
/**
 * Profil tanıtım videosu (YouTube / Vimeo)
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

add_action('add_meta_boxes', 'hive_video_metabox');
function hive_video_metabox() {
    add_meta_box(
        'hive_video',
        __('Tanıtım Videosu', 'hive-ultra-premium'),
        'hive_video_metabox_callback',
        'companion_profile',
        'normal',
        'high'
    );
}

function hive_video_metabox_callback($post) {
    wp_nonce_field('hive_video_save', 'hive_video_nonce');
    $video_url = get_post_meta($post->ID, 'video_url', true);
    ?>
    <p>
        <label for="video_url"><strong><?php esc_html_e('YouTube veya Vimeo linki', 'hive-ultra-premium'); ?></strong></label>
    </p>
    <input type="url" id="video_url" name="video_url" value="<?php echo esc_attr($video_url); ?>" style="width:100%;" placeholder="https://www.youtube.com/watch?v=... veya https://vimeo.com/...">
    <p class="description"><?php esc_html_e('Video yoksa profil sayfasında gösterilmez.', 'hive-ultra-premium'); ?></p>
    <?php
}

add_action('save_post_companion_profile', 'hive_save_video');
function hive_save_video($post_id) {
    if (!isset($_POST['hive_video_nonce']) || !wp_verify_nonce($_POST['hive_video_nonce'], 'hive_video_save')) {
        return;
    }
    if (defined('DOING_AUTOSAVE') && DOING_AUTOSAVE) {
        return;
    }
    if (!current_user_can('edit_post', $post_id)) {
        return;
    }
    if (isset($_POST['video_url'])) {
        $url = esc_url_raw(trim($_POST['video_url']));
        if ($url) {
            update_post_meta($post_id, 'video_url', $url);
        } else {
            delete_post_meta($post_id, 'video_url');
        }
    }
}

/**
 * Video embed HTML
 */
function hive_render_profile_video($post_id = null) {
    $post_id = $post_id ? (int) $post_id : get_the_ID();
    $video_url = get_post_meta($post_id, 'video_url', true);
    if (empty($video_url)) {
        return;
    }

    $embed = wp_oembed_get($video_url, array('width' => 800));
    if (!$embed) {
        return;
    }

    echo '<section class="profile-video" aria-label="' . esc_attr__('Tanıtım Videosu', 'hive-ultra-premium') . '">';
    echo '<h3 class="profile-video-title">🎬 ' . esc_html__('Tanıtım Videosu', 'hive-ultra-premium') . '</h3>';
    echo '<div class="profile-video-embed">' . $embed . '</div>';
    echo '</section>';
}

/**
 * VideoObject schema (Google zengin sonuçlar)
 */
add_action('wp_head', 'hive_video_schema', 7);
function hive_video_schema() {
    if (!is_singular('companion_profile')) {
        return;
    }

    $post_id   = get_the_ID();
    $video_url = get_post_meta($post_id, 'video_url', true);
    if (empty($video_url)) {
        return;
    }

    $embed = wp_oembed_get($video_url);
    if (!$embed) {
        return;
    }

    $thumb = get_the_post_thumbnail_url($post_id, 'large') ?: hive_ultra_placeholder_url();
    $title = get_the_title($post_id) . ' – Tanıtım Videosu';
    $desc  = get_the_title($post_id) . ' Kuşadası escort tanıtım videosu.';

    ?>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "VideoObject",
  "name": <?php echo wp_json_encode($title); ?>,
  "description": <?php echo wp_json_encode($desc); ?>,
  "thumbnailUrl": <?php echo wp_json_encode($thumb); ?>,
  "uploadDate": "<?php echo esc_attr(get_the_date('c')); ?>",
  "contentUrl": <?php echo wp_json_encode($video_url); ?>,
  "embedUrl": <?php echo wp_json_encode($video_url); ?>,
  "publisher": {
    "@type": "Organization",
    "name": "Hive Ultra Premium",
    "url": "<?php echo esc_url(home_url('/')); ?>"
  }
}
</script>
    <?php
}
