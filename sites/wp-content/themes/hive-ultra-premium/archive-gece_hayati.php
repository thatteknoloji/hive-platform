<?php
/**
 * Gece hayatı rehberi arşivi
 *
 * @package Hive_Ultra_Premium
 */

get_header();
?>

<main id="main-content" class="site-main">
    <div class="container">
        <?php if (function_exists('hive_breadcrumb')) {
            hive_breadcrumb();
        } ?>

        <header class="section-header">
            <h1>
                <?php
                if (is_tax()) {
                    single_term_title();
                } else {
                    esc_html_e('Kuşadası Gece Hayatı Rehberi', 'hive-ultra-premium');
                }
                ?>
            </h1>
            <?php if (term_description()) : ?>
                <div class="archive-description"><?php echo term_description(); ?></div>
            <?php else : ?>
                <p class="archive-description"><?php esc_html_e('180+ mekan rehberi — mahalle, saat dilimi ve mekan türüne göre filtreleyin.', 'hive-ultra-premium'); ?></p>
            <?php endif; ?>
        </header>

        <?php if (have_posts()) : ?>
            <div class="gece-hayati-grid">
                <?php
                while (have_posts()) :
                    the_post();
                    $mahalle = get_the_terms(get_the_ID(), 'gece_mahalle');
                    $saat    = get_the_terms(get_the_ID(), 'gece_saat');
                    ?>
                    <article class="gece-hayati-card">
                        <h2 class="gece-hayati-card-title">
                            <a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
                        </h2>
                        <div class="gece-hayati-card-meta">
                            <?php if ($mahalle && !is_wp_error($mahalle)) : ?>
                                <span>📍 <?php echo esc_html($mahalle[0]->name); ?></span>
                            <?php endif; ?>
                            <?php if ($saat && !is_wp_error($saat)) : ?>
                                <span>🕐 <?php echo esc_html($saat[0]->name); ?></span>
                            <?php endif; ?>
                        </div>
                        <?php if (has_excerpt()) : ?>
                            <p class="gece-hayati-card-excerpt"><?php echo esc_html(wp_trim_words(get_the_excerpt(), 28)); ?></p>
                        <?php endif; ?>
                        <a href="<?php the_permalink(); ?>" class="btn btn-outline btn-small"><?php esc_html_e('Rehberi Oku', 'hive-ultra-premium'); ?></a>
                    </article>
                <?php endwhile; ?>
            </div>
            <div class="pagination"><?php the_posts_pagination(); ?></div>
        <?php else : ?>
            <p><?php esc_html_e('Henüz mekan rehberi eklenmemiş.', 'hive-ultra-premium'); ?></p>
        <?php endif; ?>
    </div>
</main>

<?php get_footer(); ?>
