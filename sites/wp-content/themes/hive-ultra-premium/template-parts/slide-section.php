<?php
/**
 * Horizontal slide section wrapper — otomatik sağdan sola kaydırma
 *
 * @package Hive_Ultra_Premium
 *
 * @var string $args['title'] Section title
 * @var WP_Query $args['query'] Profile query
 */

if (empty($args['query']) || !$args['query']->have_posts()) {
    return;
}

$title    = isset($args['title']) ? $args['title'] : '';
$query    = $args['query'];
$show_fav = !empty($args['show_fav']);
$cols     = isset($args['cols']) ? (int) $args['cols'] : 0;
$section_class = 'slide-section';
if ($cols > 0) {
    $section_class .= ' slide-section--cols-' . $cols;
}

$posts = array();
while ($query->have_posts()) {
    $query->the_post();
    $posts[] = get_post();
}
wp_reset_postdata();

if (empty($posts)) {
    return;
}

/* ~40px/sn — kart sayısına göre süre */
$marquee_duration = max(28, min(90, (int) (count($posts) * 2.8)));
?>
<section class="<?php echo esc_attr($section_class); ?>">
    <?php if ($title) : ?>
        <h2 class="slide-title"><?php echo esc_html($title); ?></h2>
    <?php endif; ?>
    <div class="slide-container slide-marquee" tabindex="0" aria-label="<?php echo esc_attr($title); ?>" data-marquee="1" style="--marquee-duration: <?php echo esc_attr($marquee_duration); ?>s;">
        <div class="slide-marquee-viewport">
            <div class="slide-marquee-track">
                <div class="slide-track">
                    <?php
                    foreach ($posts as $post) {
                        get_template_part('template-parts/profile', 'card', array('post' => $post, 'show_fav' => $show_fav));
                    }
                    ?>
                </div>
                <div class="slide-track slide-track--clone" aria-hidden="true">
                    <?php
                    foreach ($posts as $post) {
                        get_template_part('template-parts/profile', 'card', array('post' => $post, 'show_fav' => $show_fav));
                    }
                    ?>
                </div>
            </div>
        </div>
    </div>
</section>
