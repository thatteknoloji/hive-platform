<?php
/**
 * Erotik hikaye kartı
 *
 * @package Hive_Ultra_Premium
 */

$lokasyon = get_post_meta(get_the_ID(), 'story_lokasyon', true);
$terms    = get_the_terms(get_the_ID(), 'story_category');
$cat      = ($terms && !is_wp_error($terms)) ? $terms[0]->name : '';
$likes    = function_exists('hive_story_likes') ? hive_story_likes() : 0;
?>
<article class="erotic-story-card">
    <a href="<?php the_permalink(); ?>" class="erotic-story-card-link">
        <div class="erotic-story-card-image">
            <?php if (has_post_thumbnail()) : ?>
                <?php the_post_thumbnail('medium', array('loading' => 'lazy')); ?>
            <?php else : ?>
                <img src="<?php echo esc_url(hive_ultra_placeholder_url()); ?>" alt="" loading="lazy">
            <?php endif; ?>
        </div>
        <div class="erotic-story-card-body">
            <?php if ($cat) : ?>
                <span class="erotic-story-card-cat"><?php echo esc_html($cat); ?></span>
            <?php endif; ?>
            <h3><?php the_title(); ?></h3>
            <?php if ($lokasyon) : ?>
                <span class="erotic-story-card-loc">📍 <?php echo esc_html($lokasyon); ?></span>
            <?php endif; ?>
            <p class="erotic-story-card-excerpt"><?php echo esc_html(wp_trim_words(get_the_excerpt(), 18)); ?></p>
            <span class="erotic-story-card-likes">❤️ <?php echo esc_html($likes); ?></span>
        </div>
    </a>
</article>
