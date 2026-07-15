import './AboutPage.css';

export default function AboutPage() {
  return (
    <div className="about-page">
      <h1>
        About Solmu
      </h1>
      <div className="about-content">
        <p>
          Solmu (Finnish for "knot") is an attempt to tie together the web's guitar resources, connect us more 
          deeply to our repertoire, and make guitar music accessible to everyone.
        </p>
        <p>
          The inspiration for this database came to me as a young classical guitar student trying to pick 
          repertoire for my recitals. I was always looking for hidden gems to complement the 100 or so canonical pieces 
          that everyone else splayed, but the research this required was exhausting. The music
          was scattered across different corners of the web, buried in forums, composer websites, 
          and personal collections.
        </p>
        <p>
          This experience was made worse by search algorithms, which heavily weighted already popular music. 
          The same pieces kept surfacing while the vast majority remained invisible. New music would get 
          played once and then forgotten. It struck me that no one even knew how 
          many published guitar works actually existed.
        </p>
        <p>
          So, I decided to create a centralized repository without the bias of algorithms. A place where new 
          music sits right alongside the canon, where a composer with one work has the same visibility 
          as Sor or Tárrega. A place where guitarists have the freedom to discover and choose based on their 
          own tastes and needs, not what's trending or what an algorithm thinks they should hear.
        </p>
        <p>
          <em>-Jesse Washburn, Developer of Solmu</em>
        </p>
      </div>
    </div>
  );
}
