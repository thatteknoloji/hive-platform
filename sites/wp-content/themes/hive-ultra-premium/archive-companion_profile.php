<?php
/**
 * Companion profile archive – row list view
 *
 * @package Hive_Ultra_Premium
 */

get_header();

$cat_term     = is_tax('companion_category') ? get_queried_object() : null;
$show_children = $cat_term && function_exists('hive_term_shows_child_tree') && hive_term_shows_child_tree($cat_term);
?>

<main id="main-content" class="site-main">
    <div class="container">
        <?php if (function_exists('hive_breadcrumb')) {
            hive_breadcrumb();
        } ?>

        <header class="section-header">
            <h1>
                <?php
                if (is_tax('companion_category')) {
                    single_term_title();
                } else {
                    esc_html_e('VIP Profiller', 'hive-ultra-premium');
                }
                ?>
            </h1>
            <?php if (is_tax('companion_category') && $cat_term && $cat_term->parent) :
                $parent = get_term($cat_term->parent, 'companion_category');
                if ($parent && !is_wp_error($parent)) : ?>
                    <p class="archive-description">
                        <a href="<?php echo esc_url(get_term_link($parent)); ?>"><?php echo esc_html($parent->name); ?></a>
                        <span class="hive-breadcrumb-sep"> › </span>
                        <?php echo esc_html($cat_term->name); ?>
                    </p>
                <?php endif;
            elseif (term_description()) : ?>
                <div class="archive-description"><?php echo term_description(); ?></div>
            <?php elseif (!is_tax('companion_category')) : ?>
                <p class="archive-description"><?php esc_html_e('Profilleri 10\'lu foto grid halinde inceleyin. Her sayfada 20 profil (2 satır).', 'hive-ultra-premium'); ?></p>
            <?php endif; ?>
        </header>

        <?php if (function_exists('hive_render_unified_search')) : ?>
            <div class="archive-search-bar">
                <?php hive_render_unified_search(array(
                    'id'          => 'hive-archive-search',
                    'live'        => true,
                    'placeholder' => __('İlan adı, kullanıcı adı (@telegram), kategori, mahalle ara…', 'hive-ultra-premium'),
                )); ?>
            </div>
        <?php endif; ?>

        <?php if (is_tax('companion_category') && $cat_term && !$show_children && function_exists('hive_render_category_landing_content')) : ?>
            <?php hive_render_category_landing_content($cat_term); ?>
            <?php hive_render_category_featured_profiles($cat_term, 6); ?>
        <?php endif; ?>

        <?php if ($show_children) : ?>
            <?php get_template_part('template-parts/category', 'children', array('term' => $cat_term)); ?>
            <p class="category-tree-back">
                <a href="<?php echo esc_url(hive_categories_page_url()); ?>">← <?php esc_html_e('Tüm Kategoriler', 'hive-ultra-premium'); ?></a>
            </p>
        <?php endif; ?>

        <?php if (!$show_children && have_posts()) : ?>
            <?php if (is_tax('companion_category') && $cat_term) : ?>
                <h2 class="category-all-profiles-title"><?php esc_html_e('Tüm İlanlar', 'hive-ultra-premium'); ?></h2>
            <?php endif; ?>
            <div class="profiles-photo-grid">
                <?php
                while (have_posts()) :
                    the_post();
                    get_template_part('template-parts/profile', 'grid-thumb', array('post' => get_post()));
                endwhile;
                ?>
            </div>

            <div class="pagination">
                <?php
                the_posts_pagination(array(
                    'mid_size'  => 2,
                    'prev_text' => '← ' . __('Önceki', 'hive-ultra-premium'),
                    'next_text' => __('Sonraki', 'hive-ultra-premium') . ' →',
                ));
                ?>
            </div>
        <?php elseif (!$show_children) : ?>
            <div class="no-results">
                <p><?php esc_html_e('Bu kategoride profil bulunamadı.', 'hive-ultra-premium'); ?></p>
                <a href="<?php echo esc_url(hive_categories_page_url()); ?>" class="btn btn-primary"><?php esc_html_e('Kategorilere Dön', 'hive-ultra-premium'); ?></a>
            </div>
        <?php endif; ?>

        <?php if (is_tax('companion_category')) : ?>
            <?php hive_render_category_map(); ?>
        <?php endif; ?>
    </div>
</main>

<?php get_footer(); ?>
