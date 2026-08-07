<template>
  <footer class="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-12">
    <div class="container mx-auto px-4 py-8">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <!-- 关于 -->
        <div>
          <h3 class="text-lg font-semibold text-gray-800 dark:text-white mb-4">关于海龟汤社区</h3>
          <p class="text-gray-600 dark:text-gray-400 text-sm">
            海龟汤社区是一个专注于情境推理游戏的平台，用户可以在这里发布、解答和评分各种海龟汤谜题。
          </p>
        </div>

        <!-- 快速链接 -->
        <div>
          <h3 class="text-lg font-semibold text-gray-800 dark:text-white mb-4">快速链接</h3>
          <ul class="space-y-2 text-sm">
            <li><router-link to="/soups" class="text-gray-600 dark:text-gray-400 hover:text-blue-500">海龟汤列表</router-link></li>
            <li><router-link to="/leaderboard" class="text-gray-600 dark:text-gray-400 hover:text-blue-500">排行榜</router-link></li>
            <li><router-link to="/posts" class="text-gray-600 dark:text-gray-400 hover:text-blue-500">论坛</router-link></li>
            <li><router-link to="/competitions" class="text-gray-600 dark:text-gray-400 hover:text-blue-500">比赛</router-link></li>
          </ul>
        </div>

        <!-- 联系方式 -->
        <div>
          <h3 class="text-lg font-semibold text-gray-800 dark:text-white mb-4">联系我们</h3>
          <ul class="space-y-2 text-sm text-gray-600 dark:text-gray-400">
            <li>邮箱：support@turtlesoup.com</li>
            <li>QQ 群：123456789</li>
            <li>微信公众号：海龟汤社区</li>
          </ul>
        </div>
      </div>

      <div class="border-t border-gray-200 dark:border-gray-700 mt-8 pt-8 text-center text-sm text-gray-600 dark:text-gray-400">
        <p>&copy; 2024 海龟汤社区 - Turtle Soup Community. All rights reserved.</p>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
// Footer 组件
</script>
