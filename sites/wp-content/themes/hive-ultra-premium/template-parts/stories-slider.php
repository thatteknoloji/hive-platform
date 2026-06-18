<?php
/**
 * Instagram-style stories slider
 *
 * @package Hive_Ultra_Premium
 *
 * @var int|null $args['profile_id'] Filter by profile
 */

$profile_id = isset($args['profile_id']) ? (int) $args['profile_id'] : null;
$stories    = hive_get_active_stories($profile_id, 24);

if (!$stories->have_posts()) {
    return;
}
?>

<section class="stories-section" aria-label="<?php esc_attr_e('Hikayeler', 'hive-ultra-premium'); ?>">
    <h2 class="stories-heading"><?php esc_html_e('Hikayeler', 'hive-ultra-premium'); ?></h2>
    <div class="stories-slider" tabindex="0">
        <?php
        while ($stories->have_posts()) :
            $stories->the_post();
            $sid       = get_the_ID();
            $lokasyon  = get_post_meta($sid, 'lokasyon', true);
            $ring      = hive_story_ring_url($sid);
            $full      = hive_story_gif_url($sid) ?: $ring;
            $content   = wp_strip_all_tags(get_the_content());
            $title     = get_the_title();
            $is_gif    = (bool) preg_match('/\.gif($|\?)/i', $ring) || get_post_meta($sid, '_story_gif_url', true);
            ?>
            <button
                type="button"
                class="story-item<?php echo $is_gif ? ' story-item--gif' : ''; ?>"
                data-story-title="<?php echo esc_attr($title); ?>"
                data-story-text="<?php echo esc_attr($content); ?>"
                data-story-image="<?php echo esc_url($full); ?>"
                data-story-location="<?php echo esc_attr($lokasyon); ?>"
                aria-label="<?php echo esc_attr($title); ?>"
            >
                <span class="story-ring">
                    <img src="<?php echo esc_url($ring); ?>" alt="<?php echo esc_attr($title); ?>" loading="lazy" decoding="async" width="80" height="80">
                </span>
                <span class="story-item-label"><?php echo esc_html(wp_trim_words($title, 3, '…')); ?></span>
            </button>
        <?php endwhile; ?>
    </div>
</section>
<?php
wp_reset_postdata();
