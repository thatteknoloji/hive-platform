<?php
/**
 * Profile card for horizontal slide sections
 *
 * @package Hive_Ultra_Premium
 */

$post = isset($args['post']) ? $args['post'] : get_post();
if (!$post) {
    return;
}

$show_fav  = !empty($args['show_fav']);
$post_id   = $post->ID;
$yas       = hive_ultra_get_meta($post_id, 'yas');
$lokasyon  = hive_ultra_get_meta($post_id, 'lokasyon');
$fiyat     = hive_ultra_get_meta($post_id, 'fiyat');
$telegram  = hive_ultra_get_meta($post_id, 'telegram');
$is_vip    = hive_ultra_get_meta($post_id, 'vip') === '1';
$hizmetler = get_post_meta($post_id, 'hizmetler', true);
$permalink = get_permalink($post_id);
$title     = get_the_title($post_id);
$hizmet_labels = array(
    'anal' => 'Anal', 'oral' => 'Oral', '24saat' => '24 Saat',
    'otele-gelir' => 'Otele Gelir', 'eve-gelir' => 'Eve Gelir', 'masaj' => 'Masaj',
);
$show_services = array_intersect(
    array('anal', 'oral', '24saat', 'otele-gelir', 'eve-gelir'),
    is_array($hizmetler) ? $hizmetler : array()
);
?>
<article class="profile-card">
    <div class="profile-card-image-wrap">
        <a href="<?php echo esc_url($permalink); ?>" class="profile-card-image-link" tabindex="-1">
            <?php if (has_post_thumbnail($post_id)) : ?>
                <?php echo get_the_post_thumbnail($post_id, 'hive-profile-card', array('loading' => 'lazy', 'alt' => esc_attr($title))); ?>
            <?php else : ?>
                <img src="<?php echo esc_url(hive_ultra_placeholder_url()); ?>" alt="<?php echo esc_attr($title); ?>" loading="lazy" width="560" height="420">
            <?php endif; ?>
        </a>
        <?php if ($show_fav) : ?>
            <button class="fav-btn fav-btn-card" data-id="<?php echo esc_attr($post_id); ?>" aria-label="<?php esc_attr_e('Favorilere ekle', 'hive-ultra-premium'); ?>">♡</button>
        <?php endif; ?>
        <?php if ($telegram && ($tg = hive_ultra_telegram_url($telegram))) : ?>
            <a href="<?php echo esc_url($tg); ?>" target="_blank" rel="noopener" class="card-telegram-btn" aria-label="Telegram">✈</a>
        <?php endif; ?>
    </div>
    <div class="profile-card-info">
        <a href="<?php echo esc_url($permalink); ?>" class="profile-card-link">
            <h3 class="profile-card-title"><?php echo esc_html($title); ?></h3>
        </a>
        <div class="profile-card-meta">
            <span class="profile-card-age-location">
                <?php
                $meta_parts = array();
                if ($yas) {
                    $meta_parts[] = esc_html($yas) . ' ' . esc_html__('yaş', 'hive-ultra-premium');
                }
                if ($lokasyon) {
                    $meta_parts[] = esc_html($lokasyon);
                }
                echo $meta_parts ? implode(' · ', $meta_parts) : esc_html__('Bilgi yok', 'hive-ultra-premium');
                ?>
            </span>
            <?php if ($fiyat) : ?>
                <span class="profile-card-price"><?php echo esc_html($fiyat); ?> ₺</span>
            <?php endif; ?>
        </div>
        <?php if (!empty($show_services)) : ?>
        <div class="profile-card-services">
            <?php foreach ($show_services as $s) : ?>
                <span class="mini-badge"><?php echo esc_html($hizmet_labels[$s] ?? $s); ?></span>
            <?php endforeach; ?>
        </div>
        <?php endif; ?>
        <?php if ($is_vip) : ?>
            <span class="profile-card-badge">VIP</span>
        <?php endif; ?>
    </div>
</article>
