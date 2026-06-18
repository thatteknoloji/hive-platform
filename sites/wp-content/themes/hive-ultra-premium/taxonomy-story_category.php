<?php
/**
 * Hikaye kategori arşivi
 *
 * @package Hive_Ultra_Premium
 */

get_header();
$term = get_queried_object();
?>

<main id="main-content" class="site-main">
    <div class="container">
        <header class="section-header">
            <h1><?php single_term_title(); ?></h1>
            <?php if (term_description()) : ?>
                <div class="archive-description"><?php echo term_description(); ?></div>
            <?php endif; ?>
        </header>

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
            <p><?php esc_html_e('Bu kategoride hikaye bulunamadı.', 'hive-ultra-premium'); ?></p>
        <?php endif; ?>

        <?php hive_render_category_seo_footer(); ?>
    </div>
</main>

<?php get_footer(); ?>
