<?php
/**
 * Ana sayfa – Popüler Hikayeler slider
 *
 * @package Hive_Ultra_Premium
 */

$stories = new WP_Query(array(
    'post_type'      => 'erotic_story',
    'posts_per_page' => 10,
    'orderby'        => 'meta_value_num',
    'meta_key'       => 'story_likes',
    'order'          => 'DESC',
));

if (!$stories->have_posts()) {
    $stories = new WP_Query(array(
        'post_type'      => 'erotic_story',
        'posts_per_page' => 10,
        'orderby'        => 'date',
        'order'          => 'DESC',
    ));
}

if (!$stories->have_posts()) {
    return;
}
?>

<section class="slide-section erotic-stories-home">
    <h2 class="slide-title">📖 <?php esc_html_e('Popüler Hikayeler', 'hive-ultra-premium'); ?></h2>
    <div class="slide-container" tabindex="0">
        <div class="slide-track erotic-story-track">
            <?php
            while ($stories->have_posts()) :
                $stories->the_post();
                ?>
                <div class="erotic-story-slide-card">
                    <?php get_template_part('template-parts/erotic-story', 'card'); ?>
                </div>
                <?php
            endwhile;
            wp_reset_postdata();
            ?>
        </div>
    </div>
    <p class="erotic-stories-archive-link">
        <a href="<?php echo esc_url(get_post_type_archive_link('erotic_story')); ?>" class="btn btn-secondary">
            <?php esc_html_e('Tüm Hikayeler', 'hive-ultra-premium'); ?>
        </a>
    </p>
</section>
