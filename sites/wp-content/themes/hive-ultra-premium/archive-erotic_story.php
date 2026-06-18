<?php
/**
 * Erotik hikaye arşivi
 *
 * @package Hive_Ultra_Premium
 */

get_header();
?>

<main id="main-content" class="site-main">
    <div class="container">
        <header class="section-header">
            <h1><?php esc_html_e('Erotik Hikaye Arşivi', 'hive-ultra-premium'); ?></h1>
            <p class="archive-description"><?php esc_html_e('Kuşadası escort deneyimleri, kategori ve lokasyon bazlı hikayeler.', 'hive-ultra-premium'); ?></p>
        </header>

        <?php
        $cats = get_terms(array('taxonomy' => 'story_category', 'hide_empty' => false));
        if ($cats && !is_wp_error($cats)) :
            ?>
            <div class="erotic-story-cat-nav">
                <?php foreach ($cats as $c) :
                    $link = get_term_link($c);
                    if (is_wp_error($link)) {
                        continue;
                    }
                    ?>
                    <a href="<?php echo esc_url($link); ?>" class="category-chip"><?php echo esc_html($c->name); ?></a>
                <?php endforeach; ?>
            </div>
        <?php endif; ?>

        <?php if (have_posts()) : ?>
            <div class="erotic-story-grid">
                <?php
                while (have_posts()) :
                    the_post();
                    get_template_part('template-parts/erotic-story', 'card');
                endwhile;
                ?>
            </div>
            <div class="pagination"><?php the_posts_pagination(); ?></div>
        <?php else : ?>
            <p><?php esc_html_e('Henüz hikaye eklenmemiş.', 'hive-ultra-premium'); ?></p>
        <?php endif; ?>
    </div>
</main>

<?php get_footer(); ?>
