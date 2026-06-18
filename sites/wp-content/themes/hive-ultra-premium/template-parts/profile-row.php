<?php
/**
 * Profile row for list/archive views
 *
 * @package Hive_Ultra_Premium
 */

$post = isset($args['post']) ? $args['post'] : get_post();
if (!$post) {
    return;
}

$post_id   = $post->ID;
$yas       = hive_ultra_get_meta($post_id, 'yas');
$lokasyon  = hive_ultra_get_meta($post_id, 'lokasyon');
$fiyat     = hive_ultra_get_meta($post_id, 'fiyat');
$telegram  = hive_ultra_get_meta($post_id, 'telegram');
$permalink = get_permalink($post_id);
$title     = get_the_title($post_id);
$cats      = get_the_terms($post_id, 'companion_category');
$cat_label = '';
if ($cats && !is_wp_error($cats)) {
    $cat_label = implode(', ', wp_list_pluck($cats, 'name'));
}
?>
<article class="profile-row">
    <div class="profile-row-image">
        <?php if (has_post_thumbnail($post_id)) : ?>
            <a href="<?php echo esc_url($permalink); ?>">
                <?php echo get_the_post_thumbnail($post_id, 'hive-profile-thumb', array('loading' => 'lazy', 'alt' => esc_attr($title))); ?>
            </a>
        <?php else : ?>
            <a href="<?php echo esc_url($permalink); ?>">
                <img src="<?php echo esc_url(hive_ultra_placeholder_url()); ?>" alt="<?php echo esc_attr($title); ?>" loading="lazy" width="100" height="100">
            </a>
        <?php endif; ?>
    </div>
    <div class="profile-row-info">
        <h3 class="profile-row-title">
            <a href="<?php echo esc_url($permalink); ?>"><?php echo esc_html($title); ?></a>
        </h3>
        <?php if ($yas) : ?>
            <div class="profile-row-meta">
                <?php echo esc_html($yas); ?> <?php esc_html_e('yaşında', 'hive-ultra-premium'); ?>
            </div>
        <?php endif; ?>
        <?php if ($cat_label) : ?>
            <div class="profile-row-meta profile-row-category">
                🏷️ <?php echo esc_html($cat_label); ?>
            </div>
        <?php endif; ?>
        <?php if ($telegram) : ?>
            <div class="profile-row-meta profile-row-telegram">
                ✈️ @<?php echo esc_html(ltrim($telegram, '@')); ?>
            </div>
        <?php endif; ?>
        <?php if ($lokasyon) : ?>
            <div class="profile-row-location">
                📍 <?php echo esc_html($lokasyon); ?>
            </div>
        <?php endif; ?>
    </div>
    <?php if ($fiyat) : ?>
        <div class="profile-row-price">
            <?php echo esc_html($fiyat); ?> ₺
        </div>
    <?php endif; ?>
    <div class="profile-row-button">
        <a href="<?php echo esc_url($permalink); ?>"><?php esc_html_e('Detaylar', 'hive-ultra-premium'); ?></a>
    </div>
</article>
