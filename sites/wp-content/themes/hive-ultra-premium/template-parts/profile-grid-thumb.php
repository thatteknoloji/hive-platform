<?php
/**
 * Arşiv — kompakt foto grid kartı
 *
 * @package Hive_Ultra_Premium
 */

$post = isset($args['post']) ? $args['post'] : get_post();
if (!$post) {
    return;
}

$post_id   = $post->ID;
$permalink = get_permalink($post_id);
$title     = get_the_title($post_id);
$fiyat     = hive_ultra_get_meta($post_id, 'fiyat');
$is_vip    = hive_ultra_get_meta($post_id, 'vip') === '1';
?>
<article class="profile-grid-thumb">
    <a href="<?php echo esc_url($permalink); ?>" class="profile-grid-thumb-link">
        <div class="profile-grid-thumb-image">
            <?php if (has_post_thumbnail($post_id)) : ?>
                <?php echo get_the_post_thumbnail($post_id, 'hive-profile-thumb', array('loading' => 'lazy', 'alt' => esc_attr($title))); ?>
            <?php else : ?>
                <img src="<?php echo esc_url(hive_ultra_placeholder_url()); ?>" alt="<?php echo esc_attr($title); ?>" loading="lazy" width="200" height="200">
            <?php endif; ?>
            <?php if ($is_vip) : ?>
                <span class="profile-grid-thumb-vip">VIP</span>
            <?php endif; ?>
        </div>
        <span class="profile-grid-thumb-name"><?php echo esc_html($title); ?></span>
        <?php if ($fiyat) : ?>
            <span class="profile-grid-thumb-price"><?php echo esc_html($fiyat); ?> ₺</span>
        <?php endif; ?>
    </a>
</article>
