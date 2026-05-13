import Link from 'next/link';

const ImageCard = ({ image }) => {
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow">
      <Link href={`/gallery/${image._id}`}>
        <div className="aspect-square overflow-hidden cursor-pointer">
          <img
            src={image.cloudinaryUrl}
            alt={image.title}
            className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
          />
        </div>
      </Link>
      <div className="p-4">
        <Link href={`/gallery/${image._id}`}>
          <h3 className="text-lg font-semibold text-gray-800 hover:text-blue-600 cursor-pointer">
            {image.title}
          </h3>
        </Link>
        {image.description && (
          <p className="text-gray-600 text-sm mt-2 line-clamp-2">
            {image.description}
          </p>
        )}
        {image.tags && image.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {image.tags.map((tag, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}
        <div className="flex items-center justify-between mt-4 text-sm text-gray-500">
          <span>👁 {image.views}</span>
          <span>❤️ {image.likes}</span>
          <span>
            {new Date(image.createdAt).toLocaleDateString('zh-CN', {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
            })}
          </span>
        </div>
      </div>
    </div>
  );
};

export default ImageCard;
